#!/usr/bin/env bash
# run_dev.sh — Chạy MedicalDocBot watcher ở chế độ development
# Kích hoạt .venv và chạy watcher với config.yaml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "🚀 MedicalDocBot — Development Mode"
echo "📁 Project: $PROJECT_ROOT"
echo ""

# Kiểm tra .venv
if [[ ! -d "$VENV_DIR" ]]; then
    echo "❌ Chưa có .venv. Chạy:"
    echo "   python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Kích hoạt .venv
source "$VENV_DIR/bin/activate"
echo "✅ Activated: $VENV_DIR"

# Load .env nếu có
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    echo "✅ Loaded: .env"
fi

# Tạo thư mục logs nếu chưa có
mkdir -p "$PROJECT_ROOT/logs"

# Chạy watcher
echo ""
echo "👀 Bắt đầu watch ~/MedicalDevices..."
echo "   Nhấn Ctrl+C để dừng"
echo ""

cd "$PROJECT_ROOT"
python -m app.watcher "$PROJECT_ROOT/config.yaml"
