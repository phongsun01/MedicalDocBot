import pytest
from app.search import parse_search_query

def test_parse_search_query_single():
    doc_types, keyword = parse_search_query("cấu hình máy xquang ge")
    assert doc_types == ["cau_hinh"]
    assert keyword == "máy xquang ge"

def test_parse_search_query_multiple():
    doc_types, keyword = parse_search_query("cấu hình hợp đồng ge")
    assert "cau_hinh" in doc_types
    assert "hop_dong" in doc_types
    assert keyword == "ge"

def test_parse_search_query_no_doc_type():
    doc_types, keyword = parse_search_query("máy siêu âm philips")
    assert doc_types == []
    assert keyword == "máy siêu âm philips"

def test_parse_search_query_only_doc_type():
    doc_types, keyword = parse_search_query("hướng dẫn sử dụng")
    assert doc_types == ["huong_dan_su_dung"]
    assert keyword == "sử dụng"
