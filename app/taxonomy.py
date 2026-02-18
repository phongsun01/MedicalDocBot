"""
taxonomy.py — Parse và tra cứu taxonomy thiết bị y tế.

Load file YAML 25 categories, cung cấp các hàm lookup
category, group, validate slug theo taxonomy.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Regex slug hợp lệ
SLUG_PATTERN = r"^[a-z0-9]+(?:_[a-z0-9]+)*$"


class TaxonomyError(Exception):
    """Lỗi liên quan đến taxonomy."""


class Taxonomy:
    """
    Quản lý taxonomy 25 categories thiết bị y tế.

    Ví dụ sử dụng:
        t = Taxonomy("data/taxonomy.yaml")
        cat = t.get_category("chan_doan_hinh_anh")
        group = t.get_group("chan_doan_hinh_anh", "x_quang")
    """

    def __init__(self, taxonomy_file: str | Path) -> None:
        """
        Khởi tạo và load taxonomy từ file YAML.

        Args:
            taxonomy_file: Đường dẫn đến file taxonomy.yaml
        """
        self._file = Path(taxonomy_file)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load và validate taxonomy từ YAML file."""
        if not self._file.exists():
            raise TaxonomyError(f"Không tìm thấy taxonomy file: {self._file}")

        with open(self._file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict) or "categories" not in raw:
            raise TaxonomyError("Taxonomy YAML thiếu key 'categories'")

        self._data = raw["categories"]
        logger.info("Đã load taxonomy: %d categories", len(self._data))

    def list_categories(self) -> list[dict[str, Any]]:
        """
        Trả về danh sách tất cả categories.

        Returns:
            List các dict với keys: slug, label_vi, label_en
        """
        result = []
        for slug, info in self._data.items():
            result.append(
                {
                    "slug": slug,
                    "label_vi": info.get("label_vi", slug),
                    "label_en": info.get("label_en", slug),
                    "groups": list(info.get("sub", {}).keys()),
                }
            )
        return result

    def get_category(self, category_slug: str) -> dict[str, Any] | None:
        """
        Tra cứu category theo slug.

        Args:
            category_slug: VD "chan_doan_hinh_anh"

        Returns:
            Dict thông tin category hoặc None nếu không tìm thấy
        """
        info = self._data.get(category_slug)
        if info is None:
            return None
        return {
            "slug": category_slug,
            "label_vi": info.get("label_vi", category_slug),
            "label_en": info.get("label_en", category_slug),
            "groups": info.get("sub", {}),
        }

    def get_group(self, category_slug: str, group_slug: str) -> dict[str, Any] | None:
        """
        Tra cứu group trong một category.

        Args:
            category_slug: VD "chan_doan_hinh_anh"
            group_slug: VD "x_quang"

        Returns:
            Dict thông tin group hoặc None nếu không tìm thấy
        """
        cat = self._data.get(category_slug)
        if cat is None:
            return None

        sub = cat.get("sub", {})
        label = sub.get(group_slug)
        if label is None:
            return None

        return {
            "slug": group_slug,
            "label_vi": label,
            "category_slug": category_slug,
            "category_label_vi": cat.get("label_vi", category_slug),
        }

    def list_groups(self, category_slug: str) -> list[dict[str, Any]]:
        """
        Liệt kê tất cả groups trong một category.

        Args:
            category_slug: VD "chan_doan_hinh_anh"

        Returns:
            List các dict với keys: slug, label_vi
        """
        cat = self._data.get(category_slug)
        if cat is None:
            return []

        return [
            {"slug": slug, "label_vi": label}
            for slug, label in cat.get("sub", {}).items()
        ]

    def find_category_by_label(self, label: str) -> dict[str, Any] | None:
        """
        Tìm category theo label (tiếng Việt hoặc tiếng Anh), không phân biệt hoa thường.

        Args:
            label: VD "Chẩn đoán hình ảnh" hoặc "Diagnostic imaging"

        Returns:
            Dict thông tin category hoặc None
        """
        label_lower = label.lower()
        for slug, info in self._data.items():
            if (
                info.get("label_vi", "").lower() == label_lower
                or info.get("label_en", "").lower() == label_lower
            ):
                return self.get_category(slug)
        return None

    def is_valid_category(self, category_slug: str) -> bool:
        """Kiểm tra category slug có hợp lệ không."""
        return category_slug in self._data

    def is_valid_group(self, category_slug: str, group_slug: str) -> bool:
        """Kiểm tra group slug có hợp lệ trong category không."""
        cat = self._data.get(category_slug)
        if cat is None:
            return False
        return group_slug in cat.get("sub", {})

    def get_path_label(self, category_slug: str, group_slug: str) -> str:
        """
        Trả về label đường dẫn dạng "Category > Group".

        Args:
            category_slug: VD "chan_doan_hinh_anh"
            group_slug: VD "x_quang"

        Returns:
            VD "Chẩn đoán hình ảnh > Hệ thống X-quang"
        """
        cat = self.get_category(category_slug)
        group = self.get_group(category_slug, group_slug)
        if cat and group:
            return f"{cat['label_vi']} > {group['label_vi']}"
        return f"{category_slug}/{group_slug}"

    @property
    def category_count(self) -> int:
        """Số lượng categories."""
        return len(self._data)
