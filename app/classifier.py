"""
classifier.py — Phân loại tài liệu y tế sử dụng 9router local gateway.
Trích xuất doc_type, vendor, model và các metadata quan trọng.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv
from kreuzberg import extract_file

load_dotenv(override=False)

logger = logging.getLogger(__name__)


class MedicalClassifier:
    """Xử lý phân loại file tài liệu y tế bằng 9router local gateway."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.api_key = os.getenv("NINEROUTER_API_KEY", "sk_9router")
        router_config = self.config.get("services", {}).get("9router", {})
        self.api_base = router_config.get("base_url", "http://localhost:20128/v1")
        self.model_name = router_config.get("model", "if/glm-4.7")
        self.timeout = router_config.get("timeout_seconds", 30)
        self.max_retries = router_config.get("max_retries", 5)
        self.rate_limit_seconds = router_config.get("rate_limit_seconds", 6.0)

        # Rate limiting variables (instance level)
        self._last_request_time: float = 0.0
        self._request_lock = asyncio.Lock()

    async def classify_file(self, file_path: str, max_retries: int | None = None) -> dict:
        """
        Phân loại tài liệu bằng AI qua 9router local gateway.
        Đọc nội dung file nếu có thể để tăng độ chính xác.
        """
        lock = self._request_lock

        if max_retries is None:
            max_retries = self.max_retries

        file_path_obj = Path(file_path)
        logger.info(f"Đang phân loại file: {file_path_obj.name} bằng {self.model_name}")

        # Trích xuất nội dung file (vài nghìn ký tự đầu)
        content_preview = ""
        try:
            extraction_result = await extract_file(file_path_obj)
            content_preview = extraction_result.content[:3000]  # Lấy 3000 ký tự đầu
            logger.info(f"Đã trích xuất {len(content_preview)} ký tự từ file")
        except Exception as e:
            logger.warning(
                f"Không thể trích xuất nội dung từ {file_path_obj.name}: {e}. Phân loại dựa trên tên file."
            )

        prompt = f"""
Bạn là một trợ lý chuyên gia về thiết bị y tế. Nhiệm vụ của bạn là phân loại tài liệu sau.

Tên file: {file_path_obj.name}
Nội dung trích xuất (nếu có):
{content_preview}

Dựa vào tên file và nội dung, hãy trả về kết quả dưới dạng JSON với CÁC TRƯỜNG SAU (bắt buộc đủ):
- doc_type: [ky_thuat, cau_hinh, bao_gia, trung_thau, hop_dong, so_sanh, thong_tin, lien_ket, khac]
- vendor: [Tên hãng sản xuất, viết hoa đúng chuẩn, e.g. GE Healthcare, Philips, Siemens. Ghi "Unknown" nếu không rõ]
- model: [Model thiết bị, viết hoa đúng chuẩn. Ghi "Unknown" nếu không rõ]
- category_slug: [ID nhóm thiết bị theo định dạng "nhom_lon/nhom_con", ví dụ: "noi_soi/ong_soi_mem"]
- summary: [Tóm tắt ngắn gọn nội dung tài liệu bằng tiếng Việt, tối đa 20 từ]
- confidence: [Số thực từ 0.0 đến 1.0 thể hiện mức độ chắc chắn của phân loại. 1.0 = rất chắc, 0.5 = không chắc]

Lưu ý quan trọng:
1. Nếu là tài liệu liên quan đến Tim mạch, hãy chọn category_slug là "tim_mach_can_thiep/can_thiep" hoặc tương tự.
2. Nếu tên file có đủ thông tin rõ ràng (hãng, model), đặt confidence >= 0.8.
3. Trả về DUY NHẤT một JSON object hợp lệ.
"""

        url = f"{self.api_base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        # Dùng lại retry logic đã có
        base_delay = 2.0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    # Rate Limiting
                    async with lock:
                        now = time.monotonic()
                        time_since_last = now - self._last_request_time
                        if time_since_last < self.rate_limit_seconds:
                            await asyncio.sleep(self.rate_limit_seconds - time_since_last)
                        self._last_request_time = time.monotonic()

                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()

                    try:
                        response_data = response.json()
                    except json.JSONDecodeError as de:
                        raw_text = response.text
                        # Proxy (like openrouter via 9router) might append extra data like `\n\n: OPENROUTER PROCESSING...`
                        # We must extract exactly the first valid JSON object natively.
                        start_idx = raw_text.find("{")
                        if start_idx != -1:
                            try:
                                response_data, _ = json.JSONDecoder().raw_decode(
                                    raw_text[start_idx:]
                                )
                            except json.JSONDecodeError as de2:
                                logger.error(
                                    f"RAW TEXT FROM 9ROUTER (length: {len(raw_text)}): {repr(raw_text)}"
                                )
                                raise de2
                        else:
                            raise de

                    content_str = response_data["choices"][0]["message"]["content"]

                    try:
                        # Clean up markdown code blocks
                        content_str = content_str.strip()
                        if content_str.startswith("```json"):
                            content_str = content_str[7:]
                        if content_str.startswith("```"):
                            content_str = content_str[3:]
                        if content_str.endswith("```"):
                            content_str = content_str[:-3]
                        content_str = content_str.strip()

                        # Fallback robust extraction
                        if "{" in content_str and "}" in content_str:
                            start_idx = content_str.find("{")
                            end_idx = content_str.rfind("}") + 1
                            content_str = content_str[start_idx:end_idx]

                        result = json.loads(content_str)
                        return result
                    except json.JSONDecodeError as jde:
                        logger.error(
                            f"9router trả về không đúng định dạng JSON: {content_str} | Lỗi: {jde}"
                        )
                        return {"doc_type": "khac", "summary": "Không thể phân loại tự động"}

                except httpx.HTTPStatusError as e:
                    # Catch 429 Too Many Requests
                    if e.response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt)
                            logger.warning(
                                f"Lỗi giới hạn API 9router (429). Thử lại sau {delay}s... (lần {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                f"Vượt quá số lần thử lại ({max_retries} lần) do lỗi Rate Limit: {e}"
                            )
                            raise Exception("Lỗi API (Rate Limit rớt 5 lần). Vui lòng thử lại sau.")
                    else:
                        logger.error(
                            f"Lỗi HTTP {e.response.status_code} khi gọi 9router API: {e.response.text}"
                        )
                        raise Exception(f"HTTP Error: {e.response.status_code}")
                except httpx.RequestError as e:
                    logger.error(f"Lỗi kết nối khi gọi 9router API: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2**attempt))
                    else:
                        raise Exception(str(e))
                except Exception as e:
                    logger.error(f"Lỗi không xác định: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2**attempt))
                    else:
                        raise e


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
