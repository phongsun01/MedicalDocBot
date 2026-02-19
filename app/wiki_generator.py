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
        self._jinja.filters["basename"] = lambda p: Path(p).name
        self._jinja.globals["doc_type_labels"] = DOC_TYPE_LABELS

    def _clean_name(self, s: str) -> str:
        """Sanitize filename (giữ lại tiếng Việt, thay ký tự đặc biệt bằng _)."""
        # Thay thế / bằng _ để tránh lỗi thư mục
        s = s.replace("/", "_").replace("\\", "_")
        # Loại bỏ các ký tự không an toàn khác
        return re.sub(r'[<>:"|?*]', '', s).strip()

    def _wiki_path(self, category: str, group: str, model: str) -> Path:
        """
        Đường dẫn file wiki phân cấp: wiki/Category/Group/Model.md
        """
        return self._wiki_dir / self._clean_name(category) / self._clean_name(group) / f"{self._clean_name(model)}.md"

    def _backup_file(self, path: Path) -> None:
        """Backup file trước khi ghi đè."""
        if path.exists() and self._backup:
            shutil.copy2(path, path.with_suffix(".md.bak"))

    def _replace_auto_section(self, content: str, new_section: str) -> str:
        """
        Thay thế section tự động sinh trong file MD.
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
        taxonomy: Any = None,  # Inject Taxonomy để lấy label
    ) -> Path:
        """
        Tạo hoặc cập nhật wiki MD cho một thiết bị theo cấu trúc phân cấp.
        """
        # Lấy thông tin phân cấp
        category_slug = device_info.get("category_id", "")
        # device.yaml lưu "cat/group" trong category_slug, cần split
        full_group_slug = device_info.get("category_slug", "")
        group_slug = full_group_slug.split("/")[-1] if "/" in full_group_slug else ""
        
        vendor = device_info.get("vendor", "")
        model = device_info.get("model", device_slug)
        
        # Default labels nếu không có taxonomy
        cat_label = category_slug
        group_label = group_slug
        
        if taxonomy:
            cat_data = taxonomy.get_category(category_slug)
            if cat_data:
                cat_label = cat_data["label_vi"]
                group_data = taxonomy.get_group(category_slug, group_slug)
                if group_data:
                    group_label = group_data["label_vi"]

        # Xây dựng path: wiki/Chẩn đoán hình ảnh/X-Quang/GE Optima.md
        wiki_path = self._wiki_path(cat_label, group_label, f"{vendor} {model}")
        wiki_path.parent.mkdir(parents=True, exist_ok=True)

        # Nhóm files theo doc_type
        file_groups: dict[str, list[dict[str, Any]]] = {}
        for f in files:
            dt = f.get("doc_type", "khac")
            file_groups.setdefault(dt, []).append(f)

        # Đếm theo doc_type
        counts = {dt: len(fs) for dt, fs in file_groups.items()}

        # Tìm file mới nhất
        latest: dict[str, str] = {}
        for dt, fs in file_groups.items():
            sorted_files = sorted(fs, key=lambda x: x.get("updated_at", ""), reverse=True)
            if sorted_files:
                latest[dt] = Path(sorted_files[0]["path"]).name

        # Render auto-section
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
            self._backup_file(wiki_path)
            existing = wiki_path.read_text(encoding="utf-8")
            new_content = self._replace_auto_section(existing, auto_section)
        else:
            header = f"# {vendor} {model}"
            header += f"\n\n> **Phân loại**: {cat_label} > {group_label}\n"
            header += f"> **Slug**: `{device_slug}`\n"
            new_content = f"{header}\n{_AUTO_SECTION_START}\n{auto_section}\n{_AUTO_SECTION_END}\n"

        wiki_path.write_text(new_content, encoding="utf-8")
        logger.info("✅ Wiki cập nhật: %s", wiki_path)
        return wiki_path

    def generate_indexes(self, taxonomy: Any) -> list[Path]:
        """
        Sinh Index.md tại gốc và từng folder con để Obsidain hiển thị đẹp.
        
        Returns:
            List các file index đã tạo
        """
        self._wiki_dir.mkdir(parents=True, exist_ok=True)
        created_files = []

        # 1. Root Index (Danh mục chính)
        root_index = self._wiki_dir / "00_Danh_muc_thiet_bi.md"
        lines = [
            "# 🏥 Danh mục thiết bị y tế\n",
            f"> Cập nhật: {_now_iso()}\n\n",
            "## Các nhóm thiết bị chính\n"
        ]
        
        for cat in taxonomy.list_categories():
            cat_label = cat["label_vi"]
            safe_cat_label = self._clean_name(cat_label)
            
            lines.append(f"- [[{safe_cat_label}/Index|{cat_label}]]\n")
            
            # 2. Category Index
            cat_dir = self._wiki_dir / safe_cat_label
            cat_dir.mkdir(exist_ok=True)
            cat_index = cat_dir / "Index.md"
            
            cat_lines = [
                f"# 📂 {cat_label}\n",
                f"> Slug: `{cat['slug']}`\n\n",
                "## Các phân nhóm\n"
            ]
            
            groups = taxonomy.list_groups(cat["slug"])
            for g in groups:
                group_label = g["label_vi"]
                safe_group_label = self._clean_name(group_label)
                
                cat_lines.append(f"- [[{safe_cat_label}/{safe_group_label}/Index|{group_label}]]\n")
                
                # 3. Group Index
                group_dir = cat_dir / safe_group_label
                group_dir.mkdir(exist_ok=True)
                group_index = group_dir / "Index.md"
                
                # Scan files for static list
                device_files = []
                if group_dir.exists():
                    device_files = sorted([f.name for f in group_dir.glob("*.md") if f.name != "Index.md"])

                group_lines = [
                    f"# 📑 {group_label}\n",
                    f"> Thuộc: [[{safe_cat_label}/Index|{cat_label}]]\n",
                    f"> Slug: `{g['slug']}`\n\n",
                    "## Danh sách thiết bị\n"
                ]
                
                if device_files:
                    for df in device_files:
                        group_lines.append(f"- [[{df}|{df.replace('.md', '').replace('_', ' ')}]]\n")
                else:
                    group_lines.append("*(Chưa có thiết bị nào)*\n")
                    
                group_index.write_text("".join(group_lines), encoding="utf-8")
                created_files.append(group_index)
            
            cat_index.write_text("".join(cat_lines), encoding="utf-8")
            created_files.append(cat_index)

        root_index.write_text("".join(lines), encoding="utf-8")
        created_files.append(root_index)
        
        logger.info("✅ Đã tạo %d index files", len(created_files))
        return created_files
