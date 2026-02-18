#!/usr/bin/env bash
# setup_taxonomy_folders.sh — Sinh cây thư mục ~/MedicalDevices từ taxonomy.yaml
# Idempotent: chạy lại không xóa folder có sẵn, không tạo duplicate
# Không cần sudo

set -euo pipefail

# Đường dẫn gốc
MEDICAL_ROOT="${MEDICAL_DEVICES_ROOT:-$HOME/MedicalDevices}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TAXONOMY_FILE="$PROJECT_ROOT/data/taxonomy.yaml"

echo "🏗️  Tạo cây thư mục MedicalDevices"
echo "📁 Root: $MEDICAL_ROOT"
echo "📋 Taxonomy: $TAXONOMY_FILE"
echo ""

# Kiểm tra taxonomy file tồn tại
if [[ ! -f "$TAXONOMY_FILE" ]]; then
    echo "❌ Không tìm thấy: $TAXONOMY_FILE"
    exit 1
fi

# Kiểm tra Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Cần Python 3.11+"
    exit 1
fi

# Dùng Python để parse YAML và tạo folders
python3 - <<'PYTHON_SCRIPT'
import sys
import os
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ Cần cài pyyaml: pip install pyyaml")
    sys.exit(1)

medical_root = Path(os.environ.get("MEDICAL_DEVICES_ROOT", Path.home() / "MedicalDevices"))
script_dir = Path(__file__).parent if "__file__" in dir() else Path.cwd()
project_root = script_dir.parent
taxonomy_file = project_root / "data" / "taxonomy.yaml"

# Subfolders chuẩn cho mỗi device (tạo sẵn ở level category/group)
STANDARD_SUBFOLDERS = []  # Subfolders chỉ tạo khi có device cụ thể

with open(taxonomy_file, encoding="utf-8") as f:
    data = yaml.safe_load(f)

categories = data.get("categories", {})
created = 0
skipped = 0

for cat_slug, cat_info in categories.items():
    cat_dir = medical_root / cat_slug
    if not cat_dir.exists():
        cat_dir.mkdir(parents=True)
        created += 1
        print(f"  ✅ Tạo: {cat_slug}/")
    else:
        skipped += 1

    # Tạo subfolders cho từng group
    for group_slug in cat_info.get("sub", {}).keys():
        group_dir = cat_dir / group_slug
        if not group_dir.exists():
            group_dir.mkdir(parents=True)
            created += 1
            print(f"  ✅ Tạo: {cat_slug}/{group_slug}/")
        else:
            skipped += 1

# Tạo thư mục wiki và cache
for extra in ["wiki/devices", ".cache/extracted", ".backup"]:
    extra_dir = medical_root / extra
    if not extra_dir.exists():
        extra_dir.mkdir(parents=True)
        print(f"  ✅ Tạo: {extra}/")

print(f"\n✅ Hoàn thành: {created} thư mục mới, {skipped} đã có sẵn")
print(f"📁 Root: {medical_root}")
PYTHON_SCRIPT

echo ""
echo "✅ setup_taxonomy_folders.sh hoàn thành"
