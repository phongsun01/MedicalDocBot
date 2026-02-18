"""
taxonomy.py — Parse và tra cứu taxonomy thiết bị y tế
Nguồn dữ liệu: data/taxonomy.yaml (25 nhóm theo TT 30/2015 + NĐ 98/2021)
Cung cấp API tra cứu category/group cho toàn hệ thống.
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from app.config import TAXONOMY_PATH

logger = logging.getLogger("medicalbot.taxonomy")


@dataclass
class GroupInfo:
    """Thông tin một nhóm thiết bị (sub-category)."""
    slug: str
    vi: str
    en: str
    category_slug: str  # slug của category cha


@dataclass
class CategoryInfo:
    """Thông tin một danh mục thiết bị y tế."""
    id: str           # vd: "01_chan_doan_hinh_anh"
    slug: str         # vd: "chan_doan_hinh_anh"
    vi: str           # vd: "Chẩn đoán hình ảnh"
    en: str           # vd: "Diagnostic imaging"
    groups: list[GroupInfo] = field(default_factory=list)


class TaxonomyStore:
    """
    Kho taxonomy thiết bị y tế.
    Load từ YAML một lần, tra cứu O(1) qua dict.
    """

    def __init__(self, yaml_path: Path = TAXONOMY_PATH) -> None:
        self._yaml_path = yaml_path
        self._categories: dict[str, CategoryInfo] = {}   # key: category slug
        self._groups: dict[str, GroupInfo] = {}           # key: "cat_slug/group_slug"
        self._load()

    def _load(self) -> None:
        """Đọc và parse taxonomy YAML vào bộ nhớ."""
        try:
            with open(self._yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error("Không tìm thấy taxonomy YAML: %s", self._yaml_path)
            raise
        except yaml.YAMLError as exc:
            logger.error("Lỗi parse taxonomy YAML: %s", exc)
            raise

        for cat_data in data.get("categories", []):
            groups: list[GroupInfo] = []
            for grp in cat_data.get("groups", []):
                group_info = GroupInfo(
                    slug=grp["slug"],
                    vi=grp["vi"],
                    en=grp["en"],
                    category_slug=cat_data["slug"],
                )
                groups.append(group_info)
                # Index theo "cat_slug/group_slug"
                key = f"{cat_data['slug']}/{grp['slug']}"
                self._groups[key] = group_info

            cat_info = CategoryInfo(
                id=cat_data["id"],
                slug=cat_data["slug"],
                vi=cat_data["vi"],
                en=cat_data["en"],
                groups=groups,
            )
            self._categories[cat_data["slug"]] = cat_info

        logger.info(
            "Taxonomy đã load: %d categories, %d groups",
            len(self._categories),
            len(self._groups),
        )

    # ── API tra cứu ───────────────────────────────────────────────────────────

    def get_category(self, cat_slug: str) -> Optional[CategoryInfo]:
        """Tra cứu category theo slug. Trả None nếu không tìm thấy."""
        return self._categories.get(cat_slug)

    def get_group(self, cat_slug: str, group_slug: str) -> Optional[GroupInfo]:
        """Tra cứu group theo cat_slug + group_slug. Trả None nếu không tìm thấy."""
        return self._groups.get(f"{cat_slug}/{group_slug}")

    def list_all_categories(self) -> list[CategoryInfo]:
        """Trả danh sách tất cả categories, sắp xếp theo id."""
        return sorted(self._categories.values(), key=lambda c: c.id)

    def list_groups(self, cat_slug: str) -> list[GroupInfo]:
        """Trả danh sách groups của một category. Trả [] nếu category không tồn tại."""
        cat = self._categories.get(cat_slug)
        return cat.groups if cat else []

    def find_group_by_slug(self, group_slug: str) -> list[GroupInfo]:
        """Tìm tất cả groups có slug khớp (có thể thuộc nhiều category)."""
        return [g for g in self._groups.values() if g.slug == group_slug]

    def category_exists(self, cat_slug: str) -> bool:
        """Kiểm tra category slug có tồn tại không."""
        return cat_slug in self._categories

    def group_exists(self, cat_slug: str, group_slug: str) -> bool:
        """Kiểm tra group slug có tồn tại trong category không."""
        return f"{cat_slug}/{group_slug}" in self._groups

    def get_folder_path_parts(self, cat_slug: str, group_slug: str) -> tuple[str, str]:
        """
        Trả (category_id, group_slug) để dùng làm đường dẫn thư mục.
        Ví dụ: ("01_chan_doan_hinh_anh", "x_quang")
        """
        cat = self._categories.get(cat_slug)
        if not cat:
            raise ValueError(f"Category không tồn tại: '{cat_slug}'")
        if not self.group_exists(cat_slug, group_slug):
            raise ValueError(f"Group không tồn tại: '{cat_slug}/{group_slug}'")
        return cat.id, group_slug


# ── Singleton instance ────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_taxonomy() -> TaxonomyStore:
    """Trả singleton TaxonomyStore (load một lần duy nhất)."""
    return TaxonomyStore()


# ── CLI test nhanh ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    tx = get_taxonomy()

    print(f"\n=== Taxonomy: {len(tx.list_all_categories())} categories ===")
    for cat in tx.list_all_categories():
        print(f"  [{cat.id}] {cat.vi} ({cat.en}) — {len(cat.groups)} groups")
        for grp in cat.groups:
            print(f"      └─ {grp.slug}: {grp.vi}")

    # Test tra cứu
    cat = tx.get_category("chan_doan_hinh_anh")
    assert cat is not None, "Lỗi: không tìm thấy chan_doan_hinh_anh"
    grp = tx.get_group("chan_doan_hinh_anh", "x_quang")
    assert grp is not None, "Lỗi: không tìm thấy x_quang"
    print(f"\n✓ get_category: {cat.vi}")
    print(f"✓ get_group: {grp.vi}")
    print("✓ taxonomy.py OK")
    sys.exit(0)
