"""
search.py — Module xử lý truy vấn tìm kiếm thông minh từ Telegram bot.
"""

from typing import Any, Tuple, Dict
from app.index_store import IndexStore
import re

# Bảng map nhanh các từ khóa tiếng Việt sang doc_type
DOC_TYPE_MAP = {
    "hợp đồng": "hop_dong",
    "hd": "hop_dong",
    "báo giá": "bao_gia",
    "chào giá": "bao_gia",
    "bg": "bao_gia",
    "kỹ thuật": "ky_thuat",
    "kt": "ky_thuat",
    "cấu hình": "cau_hinh",
    "ch": "cau_hinh",
    "thông tin": "thong_tin",
    "tt": "thong_tin",
    "trúng thầu": "trung_thau",
    "so sánh": "so_sanh",
    "ss": "so_sanh",
    "hướng dẫn": "huong_dan_su_dung",
    "hdsd": "huong_dan_su_dung",
}

def parse_search_query(raw_query: str) -> Tuple[str | None, str | None]:
    """
    Phân tách chuỗi truy vấn để nhận diện doc_type và keyword.
    Trả về: (doc_type, remaining_keyword)
    Ví dụ: "cấu hình máy xquang ge" => ("cau_hinh", "máy xquang ge")
    """
    raw_query = raw_query.lower().strip()
    detected_doc_type = None
    remaining_keyword = raw_query
    
    # Sort keys theo độ dài giảm dần để ưu tiên match từ khóa dài trước (ví dụ "hướng dẫn" trước "hướng")
    for kw in sorted(DOC_TYPE_MAP.keys(), key=len, reverse=True):
        if kw in raw_query:
            detected_doc_type = DOC_TYPE_MAP[kw]
            # Xóa keyword khỏi chuỗi để nhường chỗ cho model/vendor
            # Dùng regex để xóa word gọn gàng, tránh xóa một phần chữ
            pattern = re.compile(rf'\b{kw}\b', flags=re.IGNORECASE)
            remaining_keyword = pattern.sub('', raw_query).strip()
            # Xử lý whitespace thừa
            remaining_keyword = re.sub(r'\s+', ' ', remaining_keyword)
            break
            
    # Nếu còn lại chuỗi rỗng thì cho thành None
    if not remaining_keyword:
        remaining_keyword = None
        
    return detected_doc_type, remaining_keyword

async def execute_smart_search(store: IndexStore, raw_query: str, limit: int = 5) -> list[Dict[str, Any]]:
    """
    Phân tích query và thực thi tìm kiếm nâng cao trong cơ sở dữ liệu.
    """
    doc_type, keyword = parse_search_query(raw_query)
    
    results = await store.search(
        doc_type=doc_type,
        keyword=keyword,
        limit=limit,
        order_by="updated_at DESC"
    )
    
    return results
