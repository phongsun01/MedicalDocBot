"""
slug.py — Validate và normalize slug cho thiết bị y tế.

Slug hợp lệ: ^[a-z0-9]+(?:_[a-z0-9]+)*$
Ví dụ: x_quang_ge_optima_xr220_standard
"""

from __future__ import annotations

import re
import unicodedata

# Regex chuẩn cho slug hợp lệ
SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

# (Đã di chuyển logic xử lý sang normalize function)

# Ký tự tiếng Việt có dấu phức tạp (cần xử lý riêng)
_VIET_COMPLEX = {
    "ă": "a",
    "ắ": "a",
    "ặ": "a",
    "ằ": "a",
    "ẳ": "a",
    "ẵ": "a",
    "â": "a",
    "ấ": "a",
    "ậ": "a",
    "ầ": "a",
    "ẩ": "a",
    "ẫ": "a",
    "ê": "e",
    "ế": "e",
    "ệ": "e",
    "ề": "e",
    "ể": "e",
    "ễ": "e",
    "ô": "o",
    "ố": "o",
    "ộ": "o",
    "ồ": "o",
    "ổ": "o",
    "ỗ": "o",
    "ơ": "o",
    "ớ": "o",
    "ợ": "o",
    "ờ": "o",
    "ở": "o",
    "ỡ": "o",
    "ư": "u",
    "ứ": "u",
    "ự": "u",
    "ừ": "u",
    "ử": "u",
    "ữ": "u",
    "ỳ": "y",
    "ỵ": "y",
    "ỷ": "y",
    "ỹ": "y",
    "đ": "d",
    # Chữ hoa
    "Ă": "a",
    "Ắ": "a",
    "Ặ": "a",
    "Ằ": "a",
    "Ẳ": "a",
    "Ẵ": "a",
    "Â": "a",
    "Ấ": "a",
    "Ậ": "a",
    "Ầ": "a",
    "Ẩ": "a",
    "Ẫ": "a",
    "Ê": "e",
    "Ế": "e",
    "Ệ": "e",
    "Ề": "e",
    "Ể": "e",
    "Ễ": "e",
    "Ô": "o",
    "Ố": "o",
    "Ộ": "o",
    "Ồ": "o",
    "Ổ": "o",
    "Ỗ": "o",
    "Ơ": "o",
    "Ớ": "o",
    "Ợ": "o",
    "Ờ": "o",
    "Ở": "o",
    "Ỡ": "o",
    "Ư": "u",
    "Ứ": "u",
    "Ự": "u",
    "Ừ": "u",
    "Ử": "u",
    "Ữ": "u",
    "Ỳ": "y",
    "Ỵ": "y",
    "Ỷ": "y",
    "Ỹ": "y",
    "Đ": "d",
    # Tổ hợp dấu thanh
    "ạ": "a",
    "ả": "a",
    "ã": "a",
    "á": "a",
    "à": "a",
    "ẹ": "e",
    "ẻ": "e",
    "ẽ": "e",
    "é": "e",
    "è": "e",
    "ị": "i",
    "ỉ": "i",
    "ĩ": "i",
    "í": "i",
    "ì": "i",
    "ọ": "o",
    "ỏ": "o",
    "õ": "o",
    "ó": "o",
    "ò": "o",
    "ụ": "u",
    "ủ": "u",
    "ũ": "u",
    "ú": "u",
    "ù": "u",
}


def normalize(text: str) -> str:
    """
    Chuẩn hóa chuỗi thành slug hợp lệ.

    Quy trình:
    1. Chuyển ký tự tiếng Việt → ASCII
    2. Lowercase
    3. Thay thế ký tự không hợp lệ bằng '_'
    4. Loại bỏ '_' thừa ở đầu/cuối và liên tiếp

    Args:
        text: Chuỗi đầu vào (có thể có dấu, hoa thường, khoảng trắng)

    Returns:
        Slug hợp lệ theo regex ^[a-z0-9]+(?:_[a-z0-9]+)*$

    Ví dụ:
        >>> normalize("GE Healthcare Optima XR220")
        'ge_healthcare_optima_xr220'
        >>> normalize("Siêu âm Hitachi Arietta 60")
        'sieu_am_hitachi_arietta_60'
    """
    if not text:
        return ""

    # Bước 1: Thay ký tự tiếng Việt phức tạp
    result = ""
    for ch in text:
        result += _VIET_COMPLEX.get(ch, ch)

    # Bước 2: Unicode normalize → tách dấu → bỏ dấu
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if unicodedata.category(c) != "Mn")

    # Bước 3: Lowercase
    result = result.lower()

    # Bước 4: Thay ký tự không hợp lệ bằng '_'
    result = re.sub(r"[^a-z0-9]+", "_", result)

    # Bước 5: Bỏ '_' thừa ở đầu/cuối
    result = result.strip("_")

    # Bước 6: Gộp nhiều '_' liên tiếp thành 1
    result = re.sub(r"_+", "_", result)

    return result


def validate(slug: str) -> bool:
    """
    Kiểm tra slug có hợp lệ theo regex không.

    Args:
        slug: Chuỗi cần kiểm tra

    Returns:
        True nếu hợp lệ, False nếu không

    Ví dụ:
        >>> validate("x_quang_ge_optima_xr220_standard")
        True
        >>> validate("X-Quang GE")
        False
    """
    if not slug:
        return False
    return bool(SLUG_REGEX.match(slug))


def build_device_slug(vendor: str, model: str, variant: str = "") -> str:
    """
    Tạo device slug từ vendor + model + variant.

    Args:
        vendor: Tên hãng, VD "GE Healthcare"
        model: Tên model, VD "Optima XR220"
        variant: Biến thể (tùy chọn), VD "Standard", "Full Option"

    Returns:
        Slug hợp lệ, VD "ge_healthcare_optima_xr220_standard"

    Ví dụ:
        >>> build_device_slug("GE Healthcare", "Optima XR220", "Standard")
        'ge_healthcare_optima_xr220_standard'
        >>> build_device_slug("Hitachi", "Arietta 60", "Full Option")
        'hitachi_arietta_60_full_option'
    """
    parts = [vendor, model]
    if variant:
        parts.append(variant)

    combined = "_".join(normalize(p) for p in parts if p)
    # Gộp '_' thừa sau khi join
    combined = re.sub(r"_+", "_", combined).strip("_")
    return combined


def build_group_slug(category_slug: str, group_slug: str) -> str:
    """
    Tạo đường dẫn slug đầy đủ cho group.

    Args:
        category_slug: VD "chan_doan_hinh_anh"
        group_slug: VD "x_quang"

    Returns:
        VD "chan_doan_hinh_anh/x_quang"
    """
    return f"{category_slug}/{group_slug}"


# --- Golden samples để test ---
GOLDEN_SAMPLES = [
    "x_quang_ge_optima_xr220_standard",
    "sieu_am_hitachi_arrietta_60_fulloption",
]


def test_golden_samples() -> bool:
    """
    Kiểm tra tất cả golden samples pass regex.

    Returns:
        True nếu tất cả pass, False nếu có sample nào fail
    """
    all_pass = True
    for sample in GOLDEN_SAMPLES:
        ok = validate(sample)
        status = "✅" if ok else "❌"
        print(f"  {status} {sample}")
        if not ok:
            all_pass = False
    return all_pass


if __name__ == "__main__":
    print("=== Kiểm tra Golden Samples ===")
    ok = test_golden_samples()
    print(f"\n{'✅ Tất cả pass' if ok else '❌ Có sample fail'}")

    print("\n=== Test normalize ===")
    test_cases = [
        ("GE Healthcare Optima XR220", "ge_healthcare_optima_xr220"),
        ("Siêu âm Hitachi Arrietta 60", "sieu_am_hitachi_arrietta_60"),
        ("X-Quang GE", "x_quang_ge"),
        ("  Máy thở  Philips  ", "may_tho_philips"),
    ]
    for text, expected in test_cases:
        result = normalize(text)
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} '{text}' → '{result}' (expected: '{expected}')")
