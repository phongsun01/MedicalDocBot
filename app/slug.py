"""
slug.py — Validate và normalize slug thiết bị y tế
Regex chuẩn: ^[a-z0-9]+(?:_[a-z0-9]+)*$
Golden samples: x_quang_ge_optima_xr220_standard, sieu_am_hitachi_arrietta_60_fulloption
"""

import re
import unicodedata
import logging
from typing import Optional

from app.config import SLUG_PATTERN

logger = logging.getLogger("medicalbot.slug")

# Compile regex một lần duy nhất
_SLUG_RE = re.compile(SLUG_PATTERN)

# Bảng chuyển đổi ký tự tiếng Việt → ASCII
# (unicodedata.normalize không xử lý hết các trường hợp tiếng Việt)
_VIET_MAP: dict[str, str] = {
    "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
    "ă": "a", "ắ": "a", "ặ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a",
    "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
    "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
    "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
    "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
    "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
    "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
    "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
    "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
    "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
    "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    "đ": "d",
    # Chữ hoa (phòng trường hợp input chưa lowercase)
    "À": "a", "Á": "a", "Ả": "a", "Ã": "a", "Ạ": "a",
    "Ă": "a", "Ắ": "a", "Ặ": "a", "Ằ": "a", "Ẳ": "a", "Ẵ": "a",
    "Â": "a", "Ấ": "a", "Ầ": "a", "Ẩ": "a", "Ẫ": "a", "Ậ": "a",
    "È": "e", "É": "e", "Ẻ": "e", "Ẽ": "e", "Ẹ": "e",
    "Ê": "e", "Ế": "e", "Ề": "e", "Ể": "e", "Ễ": "e", "Ệ": "e",
    "Ì": "i", "Í": "i", "Ỉ": "i", "Ĩ": "i", "Ị": "i",
    "Ò": "o", "Ó": "o", "Ỏ": "o", "Õ": "o", "Ọ": "o",
    "Ô": "o", "Ố": "o", "Ồ": "o", "Ổ": "o", "Ỗ": "o", "Ộ": "o",
    "Ơ": "o", "Ớ": "o", "Ờ": "o", "Ở": "o", "Ỡ": "o", "Ợ": "o",
    "Ù": "u", "Ú": "u", "Ủ": "u", "Ũ": "u", "Ụ": "u",
    "Ư": "u", "Ứ": "u", "Ừ": "u", "Ử": "u", "Ữ": "u", "Ự": "u",
    "Ỳ": "y", "Ý": "y", "Ỷ": "y", "Ỹ": "y", "Ỵ": "y",
    "Đ": "d",
}


def _remove_diacritics(text: str) -> str:
    """
    Loại bỏ dấu tiếng Việt, chuyển về ASCII.
    Ưu tiên bảng _VIET_MAP, fallback unicodedata.
    """
    # Thay thế theo bảng tiếng Việt trước
    result = []
    for ch in text:
        result.append(_VIET_MAP.get(ch, ch))
    text = "".join(result)

    # Fallback: normalize NFD rồi loại combining marks
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = "".join(
        ch for ch in normalized
        if unicodedata.category(ch) != "Mn"
    )
    return ascii_text


def validate_slug(slug: str) -> bool:
    """
    Kiểm tra slug hợp lệ theo regex ^[a-z0-9]+(?:_[a-z0-9]+)*$
    
    Args:
        slug: Chuỗi cần kiểm tra
        
    Returns:
        True nếu hợp lệ, False nếu không
        
    Examples:
        >>> validate_slug("x_quang_ge_optima_xr220_standard")
        True
        >>> validate_slug("X-Quang GE")
        False
    """
    if not slug or not isinstance(slug, str):
        return False
    return bool(_SLUG_RE.match(slug))


def normalize_slug(text: str) -> str:
    """
    Chuẩn hóa chuỗi thành slug hợp lệ.
    
    Quy trình:
    1. Loại bỏ dấu tiếng Việt
    2. Lowercase
    3. Thay space, hyphen, dấu chấm → underscore
    4. Loại ký tự không phải [a-z0-9_]
    5. Gộp nhiều underscore liên tiếp thành một
    6. Trim underscore đầu/cuối
    
    Args:
        text: Chuỗi đầu vào (có thể có tiếng Việt, space, ký tự đặc biệt)
        
    Returns:
        Slug hợp lệ hoặc chuỗi rỗng nếu không thể chuẩn hóa
        
    Examples:
        >>> normalize_slug("GE Healthcare Optima XR220")
        'ge_healthcare_optima_xr220'
        >>> normalize_slug("Siêu âm Hitachi Arrietta 60")
        'sieu_am_hitachi_arrietta_60'
    """
    if not text:
        return ""

    # Bước 1: Loại dấu tiếng Việt
    text = _remove_diacritics(text)

    # Bước 2: Lowercase
    text = text.lower()

    # Bước 3: Thay space, hyphen, dấu chấm, slash → underscore
    text = re.sub(r"[\s\-./\\]+", "_", text)

    # Bước 4: Loại ký tự không phải [a-z0-9_]
    text = re.sub(r"[^a-z0-9_]", "", text)

    # Bước 5: Gộp nhiều underscore liên tiếp
    text = re.sub(r"_+", "_", text)

    # Bước 6: Trim underscore đầu/cuối
    text = text.strip("_")

    return text


def build_device_slug(
    group_slug: str,
    vendor: str,
    model: str,
    suffix: Optional[str] = None,
) -> str:
    """
    Tạo slug chuẩn cho thiết bị theo pattern:
    <group_slug>_<vendor_slug>_<model_slug>[_<suffix>]
    
    Args:
        group_slug: Slug của nhóm thiết bị (đã validate)
        vendor: Tên nhà sản xuất (vd: "GE Healthcare")
        model: Tên model (vd: "Optima XR220")
        suffix: Hậu tố tùy chọn (vd: "standard", "fulloption")
        
    Returns:
        Slug hợp lệ
        
    Raises:
        ValueError: Nếu slug kết quả không hợp lệ
        
    Examples:
        >>> build_device_slug("x_quang", "GE Healthcare", "Optima XR220", "standard")
        'x_quang_ge_healthcare_optima_xr220_standard'
    """
    parts = [
        group_slug,
        normalize_slug(vendor),
        normalize_slug(model),
    ]
    if suffix:
        parts.append(normalize_slug(suffix))

    slug = "_".join(p for p in parts if p)

    if not validate_slug(slug):
        raise ValueError(
            f"Không thể tạo slug hợp lệ từ: group='{group_slug}', "
            f"vendor='{vendor}', model='{model}', suffix='{suffix}' → '{slug}'"
        )

    return slug


# ── CLI test nhanh ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # Golden samples từ spec
    golden_samples = [
        "x_quang_ge_optima_xr220_standard",
        "sieu_am_hitachi_arrietta_60_fulloption",
    ]

    print("=== Validate golden samples ===")
    for sample in golden_samples:
        ok = validate_slug(sample)
        print(f"  {'✓' if ok else '✗'} {sample}")
        assert ok, f"Golden sample thất bại: {sample}"

    print("\n=== Normalize tests ===")
    test_cases = [
        ("GE Healthcare Optima XR220", "ge_healthcare_optima_xr220"),
        ("Siêu âm Hitachi Arrietta 60", "sieu_am_hitachi_arrietta_60"),
        ("X-Quang GE  Optima", "x_quang_ge_optima"),
        ("Máy thở Dräger Evita V300", "may_tho_drager_evita_v300"),
    ]
    for input_str, expected in test_cases:
        result = normalize_slug(input_str)
        ok = result == expected
        print(f"  {'✓' if ok else '✗'} '{input_str}' → '{result}' (expected: '{expected}')")

    print("\n=== build_device_slug ===")
    slug = build_device_slug("x_quang", "GE Healthcare", "Optima XR220", "standard")
    print(f"  ✓ {slug}")
    assert validate_slug(slug)

    print("\n✓ slug.py OK")
    sys.exit(0)
