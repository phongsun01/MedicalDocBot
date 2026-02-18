#!/usr/bin/env bash
# seed_samples.sh — Tạo 2 sample devices để test Phase Gate 1
# Idempotent: chạy lại không tạo duplicate
# Golden samples:
#   - x_quang_ge_optima_xr220_standard
#   - sieu_am_hitachi_arrietta_60_fulloption

set -euo pipefail

MEDICAL_ROOT="${MEDICAL_DEVICES_ROOT:-$HOME/MedicalDevices}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🌱 Tạo sample devices cho Phase Gate 1"
echo "📁 Root: $MEDICAL_ROOT"
echo ""

# Subfolders chuẩn cho mỗi device
SUBFOLDERS=("info" "tech" "config" "links" "price" "contracts" "compare" "other")

create_device() {
    local cat_slug="$1"
    local group_slug="$2"
    local device_slug="$3"
    local vendor="$4"
    local model="$5"
    local risk_class="${6:-C}"

    local device_dir="$MEDICAL_ROOT/$cat_slug/$group_slug/$device_slug"

    if [[ -d "$device_dir" ]]; then
        echo "  ⏭️  Đã tồn tại: $device_slug"
        return 0
    fi

    # Tạo thư mục device + subfolders
    for sub in "${SUBFOLDERS[@]}"; do
        mkdir -p "$device_dir/$sub"
    done

    # Tạo device.yaml
    local now
    now=$(python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())")

    cat > "$device_dir/device.yaml" <<YAML
vendor: "$vendor"
model: "$model"
category_id: "$cat_slug"
category_slug: "$cat_slug/$group_slug"
risk_class: "$risk_class"
year: 2020
hs_code: ""
status: "Hoạt động"
power_kw: 0
weight_kg: 0
aliases: []
links:
  fda: ""
  ce: ""
files:
  ky_thuat: []
  cau_hinh: []
  bao_gia: []
  trung_thau: []
  hop_dong: []
  so_sanh: []
  khac: []
created_at: "$now"
updated_at: "$now"
YAML

    # Tạo wiki MD placeholder
    local wiki_dir="$MEDICAL_ROOT/wiki/devices"
    mkdir -p "$wiki_dir"
    cat > "$wiki_dir/model_${device_slug}.md" <<MD
# $model — $vendor

> Device slug: \`$device_slug\`
> Category: \`$cat_slug/$group_slug\`

<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->
## 📊 Bảng tóm tắt tài liệu

| Loại tài liệu | Số file | File mới nhất |
|---------------|---------|---------------|
| 📋 Kỹ thuật | 0 | — |
| ⚙️ Cấu hình | 0 | — |
| 💰 Báo giá | 0 | — |
| 📝 Hợp đồng | 0 | — |
| 📁 Khác | 0 | — |

> Cập nhật: \`$now\`
<!-- AUTO-GENERATED: END -->
MD

    # Tạo sample files để test watcher
    echo "Sample tech document for $model" > "$device_dir/tech/sample_manual_vi.txt"
    echo "Sample config for $model" > "$device_dir/config/sample_config.txt"

    echo "  ✅ Tạo: $device_slug"
}

# --- Golden Sample 1: X-Quang GE Optima XR220 ---
create_device \
    "chan_doan_hinh_anh" \
    "x_quang" \
    "x_quang_ge_optima_xr220_standard" \
    "GE Healthcare" \
    "Optima XR220" \
    "C"

# --- Golden Sample 2: Siêu âm Hitachi Arrietta 60 ---
create_device \
    "chan_doan_hinh_anh" \
    "sieu_am" \
    "sieu_am_hitachi_arrietta_60_fulloption" \
    "Hitachi" \
    "Arrietta 60" \
    "B"

echo ""
echo "✅ seed_samples.sh hoàn thành"

# 4. Sinh Wiki (Cập nhật: Dùng cấu trúc phân cấp)
echo "📚 Đang sinh Wiki (Hierarchical structure)..."
export PYTHONPATH=$PYTHONPATH:.
python3.11 -c "
from app.wiki_generator import WikiGenerator
from app.taxonomy import Taxonomy

try:
    tax = Taxonomy('data/taxonomy.yaml')
    gen = WikiGenerator('config.yaml')
    
    # 1. Indexes
    gen.generate_indexes(tax)
    
    # 2. Update Samples
    # GE Optima XR220
    ge_info = {
        'vendor': 'GE', 'model': 'Optima XR220',
        'category_id': 'chan_doan_hinh_anh', 'category_slug': 'chan_doan_hinh_anh/x_quang',
        'device_slug': 'x_quang_ge_optima_xr220_standard'
    }
    gen.update_device_wiki('x_quang_ge_optima_xr220_standard', ge_info, [], taxonomy=tax)

    # Hitachi Arrietta 60
    hitachi_info = {
        'vendor': 'Hitachi', 'model': 'Arrietta 60',
        'category_id': 'chan_doan_hinh_anh', 'category_slug': 'chan_doan_hinh_anh/sieu_am',
        'device_slug': 'sieu_am_hitachi_arrietta_60_fulloption'
    }
    gen.update_device_wiki('sieu_am_hitachi_arrietta_60_fulloption', hitachi_info, [], taxonomy=tax)
    
    print('✅ Wiki updated successfully')
except Exception as e:
    print(f'❌ Wiki generation failed: {e}')
    exit(1)
"

echo ""
echo "📋 Kiểm tra slug validation:"
python3 -c "
import sys
sys.path.insert(0, '$(dirname "$SCRIPT_DIR")')
from app.slug import validate, GOLDEN_SAMPLES
all_ok = True
for s in GOLDEN_SAMPLES:
    ok = validate(s)
    print(f'  {\"✅\" if ok else \"❌\"} {s}')
    if not ok:
        all_ok = False
print()
print('✅ Tất cả slug hợp lệ' if all_ok else '❌ Có slug không hợp lệ')
sys.exit(0 if all_ok else 1)
"
