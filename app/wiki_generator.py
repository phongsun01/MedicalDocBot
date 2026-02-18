"""
wiki_generator.py — Sinh và cập nhật wiki Markdown cho thiết bị y tế
Idempotent: chạy nhiều lần không tạo duplicate.
Dùng marker <!-- DOC_SECTION:xxx --> để update đúng section.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.config import BASE_DIR, WIKI_DIR, assert_within_base_dir
from app.index_store import get_files_by_device, init_db
from app.taxonomy import get_taxonomy

logger = logging.getLogger("medicalbot.wiki_generator")

# Đường dẫn templates
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=True,
)

# Regex tìm section marker
_SECTION_RE = re.compile(
    r"<!-- DOC_SECTION:(?P<name>\w+) -->.*?<!-- /DOC_SECTION:(?P=name) -->",
    re.DOTALL,
)

# Mapping doc_type → tên section tiếng Việt
DOC_TYPE_LABELS: dict[str, str] = {
    "ky_thuat": "Tài liệu kỹ thuật",
    "cau_hinh": "Cấu hình",
    "hop_dong": "Hợp đồng",
    "bao_gia": "Báo giá",
    "trung_thau": "Trúng thầu",
    "so_sanh": "So sánh",
    "khac": "Khác",
}


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _build_section_content(doc_type: str, files: list[dict]) -> str:
    """
    Sinh nội dung cho một section doc_type.
    Mỗi file là một dòng markdown link.
    """
    if not files:
        return f"<!-- DOC_SECTION:{doc_type} -->\n_Chưa có tài liệu._\n<!-- /DOC_SECTION:{doc_type} -->"

    lines = [f"<!-- DOC_SECTION:{doc_type} -->"]
    for f in files:
        path = Path(f["path"])
        rel = path.relative_to(BASE_DIR) if path.is_relative_to(BASE_DIR) else path
        size_kb = (f.get("size_bytes") or 0) // 1024
        updated = (f.get("updated_at") or "")[:10]
        lines.append(f"- [{path.name}]({rel}) — {size_kb} KB — {updated}")
    lines.append(f"<!-- /DOC_SECTION:{doc_type} -->")
    return "\n".join(lines)


def update_model_wiki(
    device_slug: str,
    doc_type: str,
    file_path: Path,
    wiki_path: Optional[Path] = None,
) -> None:
    """
    Cập nhật đúng section doc_type trong model_<slug>.md.
    Không duplicate — dùng marker để replace.
    
    Args:
        device_slug: Slug thiết bị
        doc_type: Loại tài liệu (ky_thuat, hop_dong, v.v.)
        file_path: Đường dẫn file vừa được index
        wiki_path: Override đường dẫn wiki (mặc định: WIKI_DIR/model_<slug>.md)
    """
    try:
        if wiki_path is None:
            wiki_path = WIKI_DIR / f"model_{device_slug}.md"

        if not wiki_path.exists():
            logger.warning("Wiki chưa tồn tại cho '%s', bỏ qua update", device_slug)
            return

        # Lấy tất cả file của device + doc_type từ DB
        files = get_files_by_device(device_slug, doc_type)

        # Sinh nội dung section mới
        new_section = _build_section_content(doc_type, files)

        # Đọc nội dung hiện tại
        content = wiki_path.read_text(encoding="utf-8")

        # Pattern tìm section cụ thể
        section_pattern = re.compile(
            rf"<!-- DOC_SECTION:{re.escape(doc_type)} -->.*?<!-- /DOC_SECTION:{re.escape(doc_type)} -->",
            re.DOTALL,
        )

        if section_pattern.search(content):
            # Replace section hiện có
            new_content = section_pattern.sub(new_section, content)
        else:
            # Append section mới vào cuối
            new_content = content.rstrip() + f"\n\n{new_section}\n"

        if new_content != content:
            wiki_path.write_text(new_content, encoding="utf-8")
            logger.info("Đã cập nhật wiki [%s] section '%s'", device_slug, doc_type)
        else:
            logger.debug("Wiki [%s] section '%s' không thay đổi", device_slug, doc_type)

    except Exception as exc:
        logger.error(
            json.dumps(
                {
                    "op": "update_model_wiki",
                    "device_slug": device_slug,
                    "doc_type": doc_type,
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )


def create_model_wiki(
    device_slug: str,
    device_info: dict,
    wiki_path: Optional[Path] = None,
) -> Path:
    """
    Tạo mới model_<slug>.md từ template Jinja2.
    Idempotent: nếu đã tồn tại thì không ghi đè.
    
    Args:
        device_slug: Slug thiết bị
        device_info: Dict thông tin thiết bị (vendor, model, category_id, v.v.)
        wiki_path: Override đường dẫn output
        
    Returns:
        Path của file wiki đã tạo/tồn tại
    """
    if wiki_path is None:
        wiki_path = WIKI_DIR / f"model_{device_slug}.md"

    if wiki_path.exists():
        logger.info("Wiki đã tồn tại: %s (bỏ qua)", wiki_path.name)
        return wiki_path

    try:
        template = _jinja_env.get_template("model_template.md.j2")
        content = template.render(
            slug=device_slug,
            generated_at=_now_str(),
            **device_info,
        )
        wiki_path.parent.mkdir(parents=True, exist_ok=True)
        wiki_path.write_text(content, encoding="utf-8")
        logger.info("Đã tạo wiki: %s", wiki_path.name)
        return wiki_path

    except Exception as exc:
        logger.error(
            json.dumps(
                {"op": "create_model_wiki", "device_slug": device_slug, "error": str(exc)},
                ensure_ascii=False,
            )
        )
        raise


def generate_index_categories(wiki_dir: Path = WIKI_DIR) -> Path:
    """
    Sinh wiki/index_categories.md — danh sách tất cả categories.
    Idempotent: ghi đè mỗi lần chạy (nội dung tự động từ taxonomy).
    
    Returns:
        Path của file index đã sinh
    """
    tx = get_taxonomy()
    categories = tx.list_all_categories()

    lines = [
        "# Danh mục thiết bị y tế",
        "",
        f"_Cập nhật: {_now_str()}_",
        "",
        "| ID | Tên tiếng Việt | Tên tiếng Anh | Số nhóm |",
        "|---|---|---|---|",
    ]

    for cat in categories:
        lines.append(
            f"| `{cat.id}` | {cat.vi} | {cat.en} | {len(cat.groups)} |"
        )

    lines += [
        "",
        "## Chi tiết từng danh mục",
        "",
    ]

    for cat in categories:
        lines.append(f"### {cat.vi} (`{cat.slug}`)")
        lines.append("")
        for grp in cat.groups:
            lines.append(f"- **{grp.vi}** (`{grp.slug}`) — {grp.en}")
        lines.append("")

    output_path = wiki_dir / "index_categories.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Đã sinh index_categories.md (%d categories)", len(categories))
    return output_path


def generate_index_groups(wiki_dir: Path = WIKI_DIR) -> Path:
    """
    Sinh wiki/index_groups.md — danh sách tất cả groups phẳng.
    
    Returns:
        Path của file index đã sinh
    """
    tx = get_taxonomy()
    categories = tx.list_all_categories()

    lines = [
        "# Danh sách nhóm thiết bị y tế",
        "",
        f"_Cập nhật: {_now_str()}_",
        "",
        "| Nhóm slug | Tên tiếng Việt | Danh mục |",
        "|---|---|---|",
    ]

    for cat in categories:
        for grp in cat.groups:
            lines.append(
                f"| `{grp.slug}` | {grp.vi} | {cat.vi} |"
            )

    output_path = wiki_dir / "index_groups.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    total_groups = sum(len(c.groups) for c in categories)
    logger.info("Đã sinh index_groups.md (%d groups)", total_groups)
    return output_path


def regenerate_all_indexes(wiki_dir: Path = WIKI_DIR) -> None:
    """Sinh lại tất cả index files."""
    generate_index_categories(wiki_dir)
    generate_index_groups(wiki_dir)
    logger.info("Đã sinh lại tất cả wiki indexes")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    init_db()
    regenerate_all_indexes()
    print(f"✓ Đã sinh wiki indexes tại: {WIKI_DIR}")
    sys.exit(0)
