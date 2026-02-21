"""
classifier.py — Phân loại tài liệu y tế sử dụng Gemini Generative AI.
Trích xuất doc_type, vendor, model và các metadata quan trọng.
"""

import os
import json
import logging
import httpx
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class MedicalClassifier:
    """Xử lý phân loại file tài liệu y tế bằng Gemini."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.api_key = os.getenv("NINEROUTER_API_KEY", "sk_9router")
        router_config = self.config.get("services", {}).get("9router", {})
        self.api_base = router_config.get("base_url", "http://localhost:20128/v1")
        self.model_name = router_config.get("model", "if/glm-4.7")
        self.timeout = router_config.get("timeout_seconds", 30)
        self.max_retries = router_config.get("max_retries", 5)

    # Rate limiting variables (class level)
    _last_request_time: float = 0.0
    _request_lock: Any = None

    async def classify_file(self, file_path: str) -> Dict[str, Any]:
        """
        Gửi file đến Gemini để phân loại với rate limiting và retry.
        """
        import asyncio
        import time
        if MedicalClassifier._request_lock is None:
            MedicalClassifier._request_lock = asyncio.Lock()

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        logger.info(f"Đang phân loại file: {path.name} bằng {self.model_name}")

        # Prompt hướng dẫn Gemini
        valid_types = self.config.get('valid_doc_types', ['ky_thuat', 'bao_gia', 'hop_dong', 'khac'])
        prompt = f"""
        Bạn là một chuyên gia về thiết bị y tế. Hãy phân loại tài liệu sau:
        Tên file: {path.name}
        
        Nhiệm vụ:
        1. Xác định 'doc_type' từ danh sách: {valid_types}
        2. Trích xuất 'vendor' (Hãng sản xuất).
        3. Trích xuất 'model' (Mã hiệu thiết bị).
        4. Xác định 'category' phù hợp dựa trên nội dung.
        5. Tóm tắt nội dung tài liệu trong 1 câu tiếng Việt.

        Trả về kết quả dưới định dạng JSON duy nhất như sau:
        {{
            "doc_type": "...",
            "vendor": "...",
            "model": "...",
            "device_slug": "...",
            "category_slug": "...", 
            "summary": "..."
        }}
        
        Lưu ý quan trọng:
        - "category_slug" PHẢI khớp với cấu trúc thư mục hiện có nếu có thể (VD: chan_doan_hinh_anh/x_quang, tim_mach/can_thiep, ...).
        - Nếu không chắc chắn, hãy để trống hoặc suy luận logic nhất từ tên thiết bị.
        - Đừng quy chụp mọi thứ vào 'tim_mach' trừ khi nó thực sự liên quan đến mạch vành, stent, DSA.
        """

        max_retries = self.max_retries
        base_delay = 2
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    # Thực hiện Rate Limiting (1 request / 6 seconds -> max 10 RPM for free tier)
                    async with MedicalClassifier._request_lock:
                        now = time.monotonic()
                        time_since_last = now - MedicalClassifier._last_request_time
                        if time_since_last < 6.0:
                            await asyncio.sleep(6.0 - time_since_last)
                        MedicalClassifier._last_request_time = time.monotonic()

                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                    # Trích xuất JSON từ phản hồi API OpenAI standard
                    response_data = response.json()
                    content_str = response_data['choices'][0]['message']['content']
                    
                    try:
                        result = json.loads(content_str)
                        return result
                    except json.JSONDecodeError:
                        logger.error(f"9router trả về không đúng định dạng JSON: {content_str}")
                        return {"doc_type": "khac", "summary": "Không thể phân loại tự động"}
                        
                except httpx.HTTPStatusError as e:
                    # Catch 429 Too Many Requests
                    if e.response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Lỗi giới hạn API 9router (429). Thử lại sau {delay}s... (lần {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"Vượt quá số lần thử lại ({max_retries} lần) do lỗi Rate Limit: {e}")
                            raise Exception("Lỗi API (Rate Limit rớt 5 lần). Vui lòng thử lại sau.")
                    else:
                        logger.error(f"Lỗi HTTP {e.response.status_code} khi gọi 9router API: {e.response.text}")
                        raise Exception(f"HTTP Error: {e.response.status_code}")
                except httpx.RequestError as e:
                    logger.error(f"Lỗi kết nối khi gọi 9router API: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                    else:
                        raise Exception(str(e))
                except Exception as e:
                    logger.error(f"Lỗi không xác định: {e}")
                    raise Exception(str(e))

async def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python classifier.py <file_path>")
        return

    classifier = MedicalClassifier()
    result = await classifier.classify_file(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
