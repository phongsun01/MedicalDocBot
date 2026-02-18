#!/usr/bin/env bash
# run_dev.sh — Chạy watcher + bot song song (dev mode)
# Dừng bằng Ctrl+C
# Chạy: bash scripts/run_dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Kích hoạt venv nếu có
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Kiểm tra .env
if [[ ! -f ".env" ]]; then
    echo "⚠️  Chưa có file .env. Sao chép .env.example và điền giá trị:"
    echo "   cp .env.example .env"
    exit 1
fi

# Kiểm tra bot token
BOT_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" 2>/dev/null || echo "")
if [[ -z "$BOT_TOKEN" || "$BOT_TOKEN" == "your_bot_token_here" ]]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN chưa được cấu hình trong .env"
    exit 1
fi

echo "=== MedicalDocBot Dev Mode ==="
echo "Khởi động watcher + Telegram bot..."
echo "Dừng bằng Ctrl+C"
echo ""

# Khởi động watcher trong background
python -m app.watcher &
WATCHER_PID=$!
echo "✓ Watcher PID: $WATCHER_PID"

# Khởi động Telegram bot trong background
python -m app.telegram_bot &
BOT_PID=$!
echo "✓ Telegram Bot PID: $BOT_PID"

echo ""
echo "Cả hai service đang chạy. Nhấn Ctrl+C để dừng."

# Cleanup khi nhận Ctrl+C
cleanup() {
    echo ""
    echo "Đang dừng services..."
    kill "$WATCHER_PID" 2>/dev/null || true
    kill "$BOT_PID" 2>/dev/null || true
    wait "$WATCHER_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
    echo "✓ Đã dừng tất cả services"
}

trap cleanup INT TERM

# Chờ cho đến khi bị interrupt
wait
