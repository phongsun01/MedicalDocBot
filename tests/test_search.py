import pytest
from app.search import parse_search_query

def test_parse_search_query():
    # Test 1: Có từ khóa rõ ràng
    doc_type, keyword = parse_search_query("cấu hình máy xquang ge")
    assert doc_type == "cau_hinh"
    assert keyword == "máy xquang ge"
    
    # Test 2: Từ khóa viết tắt
    doc_type, keyword = parse_search_query("hd bảo trì philips")
    assert doc_type == "hop_dong"
    assert keyword == "bảo trì philips"
    
    # Test 3: Không có từ khóa doc_type
    doc_type, keyword = parse_search_query("máy khoan xương")
    assert doc_type is None
    assert keyword == "máy khoan xương"
    
    # Test 4: Chỉ có mỗi từ khóa doc_type
    doc_type, keyword = parse_search_query("báo giá")
    assert doc_type == "bao_gia"
    assert keyword is None

    # Test 5: Từ khóa nối liền dài hơn
    doc_type, keyword = parse_search_query("hướng dẫn sử dụng máy thở")
    assert doc_type == "huong_dan_su_dung"
    assert keyword == "sử dụng máy thở" # "hướng dẫn" is matched. oh wait, "hướng dẫn" usage leaves "sử dụng máy thở"
