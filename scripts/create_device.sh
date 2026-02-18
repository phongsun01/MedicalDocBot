#!/usr/bin/env bash
# create_device.sh — Wrapper shell cho create_device.py
# Tạo thư mục + device.yaml + wiki MD cho thiết bị mới
# Chạy: bash scripts/create_device.sh --category chan_doan_hinh_anh --group x_quang \
#              --vendor "GE Healthcare" --model "Optima XR220" --year 2018

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Kích hoạt venv nếu có
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

echo "=== MedicalDocBot: Create Device ==="
python -m app.create_device "$@"
