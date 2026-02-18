#!/usr/bin/env bash
# seed_samples.sh — Tạo dữ liệu mẫu để test Phase Gate 1
# Tạo 2 thiết bị mẫu + file PDF giả để test watcher + wiki update
# Chạy: bash scripts/seed_samples.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Đọc BASE_DIR
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    BASE_DIR=$(grep -E '^MEDICAL_DEVICES_DIR=' "$PROJECT_ROOT/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
fi
BASE_DIR="${BASE_DIR:-$HOME/MedicalDevices}"

# Kích hoạt venv nếu có
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

echo "=== MedicalDocBot: Seed Samples ==="
echo "BASE_DIR: $BASE_DIR"
echo ""

# ── Bước 1: Setup taxonomy folders ────────────────────────────────────────────
echo "[1/4] Setup taxonomy folders..."
bash "$SCRIPT_DIR/setup_taxonomy_folders.sh"
echo ""

# ── Bước 2: Tạo thiết bị mẫu 1 — GE Optima XR220 ─────────────────────────────
echo "[2/4] Tạo thiết bị mẫu: GE Optima XR220..."
python -m app.create_device \
    --category chan_doan_hinh_anh \
    --group x_quang \
    --vendor "GE Healthcare" \
    --model "Optima XR220" \
    --year 2018 \
    --risk-class "C" \
    --hs-code "9022.12.00" \
    --power-kw "50" \
    --weight-kg "1200" \
    --slug "x_quang_ge_optima_xr220_standard"
echo ""

# ── Bước 3: Tạo thiết bị mẫu 2 — Hitachi Arrietta 60 ─────────────────────────
echo "[3/4] Tạo thiết bị mẫu: Hitachi Arrietta 60..."
python -m app.create_device \
    --category chan_doan_hinh_anh \
    --group sieu_am \
    --vendor "Hitachi" \
    --model "Arrietta 60" \
    --year 2020 \
    --risk-class "B" \
    --slug "sieu_am_hitachi_arrietta_60_fulloption"
echo ""

# ── Bước 4: Tạo file PDF giả để test watcher ──────────────────────────────────
echo "[4/4] Tạo file PDF mẫu để test watcher..."

DEVICE1_DIR="$BASE_DIR/01_chan_doan_hinh_anh/x_quang/x_quang_ge_optima_xr220_standard"
DEVICE2_DIR="$BASE_DIR/01_chan_doan_hinh_anh/sieu_am/sieu_am_hitachi_arrietta_60_fulloption"

# Tạo file PDF giả (chỉ để test watcher, không phải PDF thực)
if [[ -d "$DEVICE1_DIR/tech" ]]; then
    echo "%PDF-1.4 GE Optima XR220 Technical Manual Sample" > "$DEVICE1_DIR/tech/brochure.pdf"
    echo "  → $DEVICE1_DIR/tech/brochure.pdf"
fi

if [[ -d "$DEVICE1_DIR/contracts" ]]; then
    echo "%PDF-1.4 GE Optima XR220 Contract Sample 2023" > "$DEVICE1_DIR/contracts/hop_dong_2023.pdf"
    echo "  → $DEVICE1_DIR/contracts/hop_dong_2023.pdf"
fi

if [[ -d "$DEVICE2_DIR/tech" ]]; then
    echo "%PDF-1.4 Hitachi Arrietta 60 Brochure Sample" > "$DEVICE2_DIR/tech/brochure.pdf"
    echo "  → $DEVICE2_DIR/tech/brochure.pdf"
fi

# ── Sinh wiki indexes ─────────────────────────────────────────────────────────
echo ""
echo "Sinh wiki indexes..."
python -m app.wiki_generator

echo ""
echo "=== Seed hoàn thành ==="
echo ""
echo "Thiết bị đã tạo:"
echo "  1. x_quang_ge_optima_xr220_standard"
echo "     → $DEVICE1_DIR"
echo "  2. sieu_am_hitachi_arrietta_60_fulloption"
echo "     → $DEVICE2_DIR"
echo ""
echo "Wiki indexes:"
echo "  → $BASE_DIR/wiki/index_categories.md"
echo "  → $BASE_DIR/wiki/index_groups.md"
echo ""
echo "Tiếp theo: chạy watcher để test Phase Gate 1"
echo "  python -m app.watcher"
