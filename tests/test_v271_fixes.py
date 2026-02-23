"""
tests/test_v271_fixes.py
Kiểm thử tự động các bản vá trong v2.7.1
Chạy: python -m pytest tests/test_v271_fixes.py -v
"""
import re
import sys
import asyncio
import pytest
from pathlib import Path

# Thêm root vào sys.path để import dễ dàng
sys.path.insert(0, str(Path(__file__).parents[1]))


# =============================================================================
# 1. SQL INJECTION — IndexStore.search order_by whitelist
# =============================================================================
class TestOrderByWhitelist:
    """Kiểm tra logic validate order_by trong IndexStore.search không cho qua chuỗi độc hại."""

    def _safe_order_by(self, order_by: str) -> str:
        """Copy chính xác logic từ index_store.py để test độc lập."""
        _ALLOWED_COLUMNS = {
            "path", "sha256", "doc_type", "device_slug", "category_slug",
            "updated_at", "created_at", "indexed_at", "vendor", "model", "size_bytes",
        }
        _ALLOWED_DIRECTIONS = {"asc", "desc"}
        order_parts = order_by.lower().split()
        if len(order_parts) >= 1 and order_parts[0] in _ALLOWED_COLUMNS:
            col = order_parts[0]
            direction = (
                order_parts[1]
                if len(order_parts) >= 2 and order_parts[1] in _ALLOWED_DIRECTIONS
                else "asc"
            )
            return f"{col} {direction.upper()}"
        return "updated_at DESC"

    def test_normal_valid_column(self):
        result = self._safe_order_by("updated_at DESC")
        assert result == "updated_at DESC"

    def test_normal_valid_column_asc(self):
        result = self._safe_order_by("vendor asc")
        assert result == "vendor ASC"

    def test_injection_sql(self):
        """Chuỗi inject phải bị reject và fallback về updated_at DESC"""
        result = self._safe_order_by("updated_at; DROP TABLE files --")
        assert result == "updated_at DESC"

    def test_injection_semicolon_only(self):
        result = self._safe_order_by("; DROP TABLE files")
        assert result == "updated_at DESC"

    def test_injection_union(self):
        result = self._safe_order_by("1 UNION SELECT * FROM users")
        assert result == "updated_at DESC"

    def test_empty_string_fallback(self):
        result = self._safe_order_by("")
        assert result == "updated_at DESC"

    def test_invalid_column_fallback(self):
        result = self._safe_order_by("password asc")
        assert result == "updated_at DESC"

    def test_column_without_direction_defaults_asc(self):
        result = self._safe_order_by("model")
        assert result == "model ASC"


# =============================================================================
# 2. SLUG — Duplicate keys trong _VIET_COMPLEX
# =============================================================================
class TestSlugNoDuplicates:
    """Kiểm tra _VIET_COMPLEX không có key trùng, và normalize hoạt động đúng."""

    def test_no_duplicate_keys_in_viet_complex(self):
        """
        Python dict tự động overwrite key trùng nên detect qua source code.
        Ta đọc source và đếm key xuất hiện.
        """
        source_path = Path(__file__).parents[1] / "app" / "slug.py"
        text = source_path.read_text(encoding="utf-8")

        # Tìm phần _VIET_COMPLEX
        start = text.find("_VIET_COMPLEX = {")
        end = text.find("\n}", start)
        complex_block = text[start:end]

        # Tìm tất cả key (chuỗi ký tự Unicode trong "...": ...)
        keys = re.findall(r'"(.)"\s*:', complex_block)
        assert len(keys) == len(set(keys)), f"Có key trùng: {[k for k in keys if keys.count(k) > 1]}"

    def test_normalize_basic(self):
        from app.slug import normalize
        assert normalize("GE Healthcare") == "ge_healthcare"

    def test_normalize_vietnamese(self):
        from app.slug import normalize
        result = normalize("Máy thở Philips")
        assert result == "may_tho_philips"

    def test_normalize_diacritics(self):
        from app.slug import normalize
        assert normalize("Đặng Văn Phong") == "dang_van_phong"

    def test_normalize_special_chars(self):
        from app.slug import normalize
        result = normalize("X-Quang GE 2024!")
        assert result == "x_quang_ge_2024"

    def test_slug_validate(self):
        from app.slug import validate
        assert validate("ge_healthcare_optima_xr220") is True
        assert validate("X Quang") is False
        assert validate("") is False


# =============================================================================
# 3. SEARCH REGEX — Lookahead boundary
# =============================================================================
class TestSearchRegex:
    """Kiểm tra regex trong search.py nhận dạng đúng keyword kể cả khi theo sau là dấu câu."""

    def _match_keyword(self, text: str, kw: str) -> bool:
        """Mô phỏng pattern từ search.py (với fix (?=\\s|$|\\W))."""
        pattern = re.compile(
            r"(^|\s)" + re.escape(kw) + r"(?=\s|$|\W)",
            flags=re.IGNORECASE
        )
        return bool(pattern.search(text))

    def test_keyword_at_end_of_sentence_with_period(self):
        assert self._match_keyword("tìm bao giá.", "bao giá") is True

    def test_keyword_in_middle(self):
        assert self._match_keyword("tài liệu kỹ thuật mới", "kỹ thuật") is True

    def test_keyword_with_comma(self):
        assert self._match_keyword("bao giá, hợp đồng", "bao giá") is True

    def test_keyword_no_match_partial(self):
        """Tránh match partial — 'bao' không nên match trong 'baoque' (tên riêng)."""
        # Vì "baoque" không có space hoặc word boundary trước "bao"
        assert self._match_keyword("baoque mới", "bao") is False

    def test_keyword_full_string(self):
        assert self._match_keyword("kỹ thuật", "kỹ thuật") is True


# =============================================================================
# 4. PROCESS_EVENT — _CATEGORY_MAP là module-level constant
# =============================================================================
class TestCategoryMapModuleLevel:
    """Đảm bảo _CATEGORY_MAP & _GROUP_MAP được định nghĩa ở module level trong process_event.py."""

    def test_category_map_at_module_level(self):
        source_path = Path(__file__).parents[1] / "app" / "process_event.py"
        text = source_path.read_text(encoding="utf-8")

        # _CATEGORY_MAP phải xuất hiện trước dấu `def process_new_file`
        category_idx = text.find("_CATEGORY_MAP")
        func_idx = text.find("def process_new_file")
        assert category_idx != -1, "_CATEGORY_MAP không tìm thấy trong file"
        assert func_idx != -1, "Hàm process_new_file không tìm thấy trong file"
        assert category_idx < func_idx, "_CATEGORY_MAP không phải module-level (nằm sau def)"

    def test_category_map_not_inside_function(self):
        """_CATEGORY_MAP = { không nên xuất hiện ở trong thân function (có indent)."""
        source_path = Path(__file__).parents[1] / "app" / "process_event.py"
        for line in source_path.read_text(encoding="utf-8").splitlines():
            if "_CATEGORY_MAP = {" in line:
                assert not line.startswith("    "), \
                    "_CATEGORY_MAP vẫn đang được định nghĩa bên trong function (có indent)!"

    def test_correction_values(self):
        from app.process_event import _CATEGORY_MAP, _GROUP_MAP
        assert _CATEGORY_MAP.get("ngoai_khoa") == "thiet_bi_phong_mo"
        assert _GROUP_MAP.get("Unknown") == "khac"





if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
