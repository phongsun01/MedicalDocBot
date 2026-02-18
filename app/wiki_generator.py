"""
wiki_generator.py — Sinh và cập nhật wiki Markdown cho thiết bị y tế.

Render model_*.md từ Jinja2 template, cập nhật đúng section,
không tạo duplicate. Sinh index_categories.md và index_groups.md.
Idempotent: chạy nhiều lần → kết quả giống nhau.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

logger = logging.getLogger(__name__)

# Marker để tìm section tự động sinh trong MD
_AUTO_SECTION_START = "<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->"
_AUTO_SECTION_END = "<!-- AUTO-GENERATED: END -->"

# Label tiếng Việt cho doc_type
DOC_TYPE_LABELS: dict[str, str] = {
    "ky_thuat": "📋 Kỹ thuật",
    "cau_hinh": "⚙️ Cấu hình",
    "bao_gia": "💰 Báo giá",
    "trung_thau": "🏆 Trúng thầu",
    "hop_dong": "📝 Hợp đồng",
    "so_sanh": "⚖️ So sánh",
    "thong_tin": "ℹ️ Thông tin",
    "lien_ket": "🔗 Liên kết",
    "khac": "📁 Khác",
}


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat()


def _format_size(size_bytes: int) -> str:
    """Định dạng kích thước file."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


class WikiGenerator:
    """
    Sinh và cập nhật wiki Markdown cho thiết bị y tế.

    Ví dụ sử dụng:
        gen = WikiGenerator("config.yaml")
        gen.update_device_wiki(
            device_slug="x_quang_ge_optima_xr220_standard",
            device_info={...},
            files=[...]
        )
        gen.generate_indexes(taxonomy)
    """

    def __init__(self, config_path: str = "config.yaml") -> None:
        import yaml as _yaml

        with open(config_path, encoding="utf-8") as f:
            self._config = _yaml.safe_load(f)

        self._wiki_dir = Path(
            os.path.expandvars(os.path.expanduser(self._config["paths"]["wiki_dir"]))
        )
        self._template_dir = Path(self._config["wiki"]["template_dir"])
        self._backup = self._config["wiki"]["backup_before_write"]

        # Jinja2 environment
        self._jinja = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            undefined=StrictUndefined,
            autoescape=False,
        )
        self._jinja.filters["format_size"] = _format_size
        self._jinja.globals["doc_type_labels"] = DOC_TYPE_LABELS

    def _wiki_path(self, device_slug: str) -> Path:
        """Đường dẫn file wiki cho thiết bị."""
        return self._wiki_dir / "devices" / f"model_{device_slug}.md"

    def _backup_file(self, path: Path) -> None:
        """Backup file trước khi ghi đè."""
        if path.exists() and self._backup:
            shutil.copy2(path, path.with_suffix(".md.bak"))

    def _replace_auto_section(self, content: str, new_section: str) -> str:
        """
        Thay thế section tự động sinh trong file MD.

        Tìm markers AUTO-GENERATED và thay nội dung giữa chúng.
        Nếu chưa có markers → append vào cuối.
        """
        pattern = re.compile(
            rf"{re.escape(_AUTO_SECTION_START)}.*?{re.escape(_AUTO_SECTION_END)}",
            re.DOTALL,
        )
        replacement = f"{_AUTO_SECTION_START}\n{new_section}\n{_AUTO_SECTION_END}"

        if pattern.search(content):
            return pattern.sub(replacement, content)
        else:
            return content.rstrip() + f"\n\n{replacement}\n"

    def update_device_wiki(
        self,
        device_slug: str,
        device_info: dict[str, Any],
        files: list[dict[str, Any]],
    ) -> Path:
        """
        Tạo hoặc cập nhật wiki MD cho một thiết bị.

        Args:
            device_slug: Slug thiết bị
            device_info: Thông tin từ device.yaml
            files: Danh sách files từ index_store

        Returns:
            Đường dẫn file wiki đã tạo/cập nhật
        """
        wiki_path = self._wiki_path(device_slug)
        wiki_path.parent.mkdir(parents=True, exist_ok=True)

        # Nhóm files theo doc_type
        file_groups: dict[str, list[dict[str, Any]]] = {}
        for f in files:
            dt = f.get("doc_type", "khac")
            file_groups.setdefault(dt, []).append(f)

        # Đếm theo doc_type
        counts = {dt: len(fs) for dt, fs in file_groups.items()}

        # Tìm file mới nhất theo doc_type
        latest: dict[str, str] = {}
        for dt, fs in file_groups.items():
            sorted_files = sorted(fs, key=lambda x: x.get("updated_at", ""), reverse=True)
            if sorted_files:
                latest[dt] = Path(sorted_files[0]["path"]).name

        # Render auto-section (bảng tóm tắt + danh sách files)
        try:
            template = self._jinja.get_template("model_template.md.j2")
        except Exception as e:
            logger.error("Không load được template: %s", e)
            raise

        auto_section = template.render(
            device_slug=device_slug,
            device_info=device_info,
            file_groups=file_groups,
            counts=counts,
            latest=latest,
            updated_at=_now_iso(),
            doc_type_labels=DOC_TYPE_LABELS,
        )

        if wiki_path.exists():
            # Cập nhật section tự động trong file hiện có
            self._backup_file(wiki_path)
            existing = wiki_path.read_text(encoding="utf-8")
            new_content = self._replace_auto_section(existing, auto_section)
        else:
            # Tạo file mới với header + auto section
            vendor = device_info.get("vendor", "")
            model = device_info.get("model", device_slug)
            header = f"# {model}"
            if vendor:
                header += f" — {vendor}"
            header += f"\n\n> Device slug: `{device_slug}`\n"
            new_content = f"{header}\n{_AUTO_SECTION_START}\n{auto_section}\n{_AUTO_SECTION_END}\n"

        wiki_path.write_text(new_content, encoding="utf-8")
        logger.info("✅ Wiki cập nhật: %s", wiki_path)
        return wiki_path

    def generate_indexes(self, taxonomy: Any) -> tuple[Path, Path]:
        """
        Sinh wiki/index_categories.md và wiki/index_groups.md.

        Args:
            taxonomy: Instance của Taxonomy class

        Returns:
            Tuple (categories_path, groups_path)
        """
        self._wiki_dir.mkdir(parents=True, exist_ok=True)

        # --- index_categories.md ---
        cats_path = self._wiki_dir / "index_categories.md"
        cats_lines = [
            "# Danh mục thiết bị y tế\n",
            f"> Cập nhật: {_now_iso()}\n",
            f"> Tổng số: {taxonomy.category_count} categories\n\n",
            "| # | Slug | Tên tiếng Việt | Tên tiếng Anh | Số nhóm |\n",
            "|---|------|----------------|---------------|----------|\n",
        ]
        for i, cat in enumerate(taxonomy.list_categories(), 1):
            groups = cat.get("groups", [])
            cats_lines.append(
                f"| {i} | `{cat['slug']}` | {cat['label_vi']} | {cat['label_en']} | {len(groups)} |\n"
            )
        cats_path.write_text("".join(cats_lines), encoding="utf-8")
        logger.info("✅ Index categories: %s", cats_path)

        # --- index_groups.md ---
        groups_path = self._wiki_dir / "index_groups.md"
        groups_lines = [
            "# Danh sách nhóm thiết bị y tế\n",
            f"> Cập nhật: {_now_iso()}\n\n",
        ]
        for cat in taxonomy.list_categories():
            groups_lines.append(f"## {cat['label_vi']}\n\n")
            groups_lines.append(f"> `{cat['slug']}`\n\n")
            groups = taxonomy.list_groups(cat["slug"])
            if groups:
                groups_lines.append("| Slug | Tên nhóm |\n")
                groups_lines.append("|------|----------|\n")
                for g in groups:
                    groups_lines.append(f"| `{g['slug']}` | {g['label_vi']} |\n")
            groups_lines.append("\n")

        groups_path.write_text("".join(groups_lines), encoding="utf-8")
        logger.info("✅ Index groups: %s", groups_path)

        return cats_path, groups_path
