"""
create_device.py — Tạo thư mục và file khởi tạo cho thiết bị y tế mới
Sinh: <BASE_DIR>/<cat_id>/<group_slug>/<device_slug>/
      ├── device.yaml
      └── (wiki được sinh tại WIKI_DIR/model_<slug>.md)
Idempotent: chạy lại không tạo duplicate.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.config import BASE_DIR, WIKI_DIR, setup_logging
from app.index_store import init_db
from app.slug import build_device_slug, validate_slug
from app.taxonomy import get_taxonomy
from app.wiki_generator import create_model_wiki

logger = logging.getLogger("medicalbot.create_device")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=True,
)

# Các thư mục con chuẩn trong mỗi device folder
DEVICE_SUBDIRS = [
    "tech",       # Tài liệu kỹ thuật
    "config",     # Cấu hình
    "contracts",  # Hợp đồng
    "price",      # Báo giá / trúng thầu
    "compare",    # So sánh
    "other",      # Khác
]


def create_device(
    category_slug: str,
    group_slug: str,
    vendor: str,
    model: str,
    year: int,
    risk_class: str = "",
    hs_code: str = "",
    status: str = "Hoạt động",
    power_kw: str = "",
    weight_kg: str = "",
    device_slug_override: str = "",
    base_dir: Path = BASE_DIR,
) -> dict:
    """
    Tạo thư mục và file khởi tạo cho thiết bị mới.
    
    Args:
        category_slug: Slug danh mục (vd: "chan_doan_hinh_anh")
        group_slug: Slug nhóm (vd: "x_quang")
        vendor: Nhà sản xuất (vd: "GE Healthcare")
        model: Tên model (vd: "Optima XR220")
        year: Năm sản xuất/nhập khẩu
        risk_class: Phân loại rủi ro (A/B/C/D)
        hs_code: Mã HS
        status: Trạng thái
        power_kw: Công suất (kW)
        weight_kg: Trọng lượng (kg)
        device_slug_override: Override slug tự động
        base_dir: Override BASE_DIR (cho testing)
        
    Returns:
        Dict với thông tin thiết bị đã tạo
        
    Raises:
        ValueError: Nếu taxonomy không hợp lệ hoặc slug không pass regex
    """
    tx = get_taxonomy()

    # Validate taxonomy
    if not tx.category_exists(category_slug):
        raise ValueError(f"Category không tồn tại: '{category_slug}'")
    if not tx.group_exists(category_slug, group_slug):
        raise ValueError(f"Group không tồn tại: '{category_slug}/{group_slug}'")

    cat = tx.get_category(category_slug)
    grp = tx.get_group(category_slug, group_slug)

    # Tạo hoặc validate slug
    if device_slug_override:
        if not validate_slug(device_slug_override):
            raise ValueError(
                f"Slug override không hợp lệ: '{device_slug_override}' "
                f"(phải match ^[a-z0-9]+(?:_[a-z0-9]+)*$)"
            )
        device_slug = device_slug_override
    else:
        device_slug = build_device_slug(group_slug, vendor, model)

    # Đường dẫn thư mục thiết bị
    device_dir = base_dir / cat.id / group_slug / device_slug

    # Tạo thư mục chính + subdirs (idempotent)
    device_dir.mkdir(parents=True, exist_ok=True)
    for subdir in DEVICE_SUBDIRS:
        (device_dir / subdir).mkdir(exist_ok=True)
        # Tạo .gitkeep để git track thư mục rỗng
        gitkeep = device_dir / subdir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    logger.info("Thư mục thiết bị: %s", device_dir)

    # Thông tin thiết bị
    now_iso = datetime.now(timezone.utc).isoformat()
    device_info = {
        "slug": device_slug,
        "vendor": vendor,
        "model": model,
        "category_id": cat.id,
        "category_slug": f"{category_slug}/{group_slug}",
        "group_slug": group_slug,
        "risk_class": risk_class,
        "year": year,
        "hs_code": hs_code,
        "status": status,
        "power_kw": power_kw,
        "weight_kg": weight_kg,
        "created_at": now_iso,
    }

    # Sinh device.yaml (idempotent)
    yaml_path = device_dir / "device.yaml"
    if not yaml_path.exists():
        template = _jinja_env.get_template("device_yaml_template.yaml.j2")
        yaml_content = template.render(**device_info)
        yaml_path.write_text(yaml_content, encoding="utf-8")
        logger.info("Đã tạo device.yaml: %s", yaml_path)
    else:
        logger.info("device.yaml đã tồn tại, bỏ qua: %s", yaml_path)

    # Sinh wiki MD (idempotent)
    wiki_path = WIKI_DIR / f"model_{device_slug}.md"
    create_model_wiki(device_slug, device_info, wiki_path)

    result = {
        "device_slug": device_slug,
        "device_dir": str(device_dir),
        "yaml_path": str(yaml_path),
        "wiki_path": str(wiki_path),
        "category": cat.vi,
        "group": grp.vi,
    }

    logger.info(
        "Thiết bị đã tạo: %s\n%s",
        device_slug,
        json.dumps(result, ensure_ascii=False, indent=2),
    )
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tạo thư mục và file khởi tạo cho thiết bị y tế mới"
    )
    parser.add_argument("--category", required=True, help="Slug danh mục (vd: chan_doan_hinh_anh)")
    parser.add_argument("--group", required=True, help="Slug nhóm (vd: x_quang)")
    parser.add_argument("--vendor", required=True, help="Nhà sản xuất (vd: 'GE Healthcare')")
    parser.add_argument("--model", required=True, help="Tên model (vd: 'Optima XR220')")
    parser.add_argument("--year", type=int, required=True, help="Năm (vd: 2018)")
    parser.add_argument("--risk-class", default="", help="Phân loại rủi ro (A/B/C/D)")
    parser.add_argument("--hs-code", default="", help="Mã HS")
    parser.add_argument("--status", default="Hoạt động", help="Trạng thái")
    parser.add_argument("--power-kw", default="", help="Công suất kW")
    parser.add_argument("--weight-kg", default="", help="Trọng lượng kg")
    parser.add_argument("--slug", default="", help="Override slug tự động")

    args = parser.parse_args()

    setup_logging()
    init_db()

    try:
        result = create_device(
            category_slug=args.category,
            group_slug=args.group,
            vendor=args.vendor,
            model=args.model,
            year=args.year,
            risk_class=args.risk_class,
            hs_code=args.hs_code,
            status=args.status,
            power_kw=args.power_kw,
            weight_kg=args.weight_kg,
            device_slug_override=args.slug,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    except ValueError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
