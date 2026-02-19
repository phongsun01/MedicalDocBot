"""
classifier.py — Phân loại tài liệu y tế sử dụng Gemini Generative AI.
Trích xuất doc_type, vendor, model và các metadata quan trọng.
"""

import os
import json
import logging
import google.generativeai as genai
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
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy trong môi trường.")
        
        genai.configure(api_key=api_key)
        # Sử dụng model ID mới nhất từ danh sách hỗ trợ
        self.model_name = "gemini-flash-latest"
        self.model = genai.GenerativeModel(self.model_name)

    async def classify_file(self, file_path: str) -> Dict[str, Any]:
        """
        Gửi file đến Gemini để phân loại.
        """
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

        try:
            # Tạm thời chỉ dùng tên file để demo nếu chưa xử lý PDF buffer hoàn chỉnh
            # Tuy nhiên Gemini support file upload. Ở đây ta dùng tên file + text context.
            response = self.model.generate_content(prompt)
            
            # Trích xuất JSON từ phản hồi (đề phòng Gemini trả thêm text)
            text = response.text
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                result = json.loads(text[json_start:json_end])
                return result
            else:
                logger.error(f"Gemini trả về không đúng định dạng JSON: {text}")
                return {"doc_type": "khac", "summary": "Không thể phân loại tự động"}
        except Exception as e:
            logger.error(f"Lỗi khi gọi Gemini API: {e}")
            return {"doc_type": "khac", "summary": str(e)}

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
