#!/bin/bash
# start.sh - Khởi động MedicalDocBot (Watcher & Telegram Bot)
# Phải chạy từ thư mục gốc của project: bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kích hoạt venv
source .venv/bin/activate
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Load biến môi trường
if [[ -f ".env" ]]; then
    set -a; source .env; set +a
fi

# Tạo thư mục logs nếu chưa có
mkdir -p logs

echo "🚀 Đang khởi động MedicalDocBot..."

# Dừng nếu đang chạy
pkill -f "app.watcher" 2>/dev/null && echo "⚠️  Watcher cũ đã dừng."
pkill -f "app.telegram_bot" 2>/dev/null && echo "⚠️  Bot cũ đã dừng."
sleep 1

# Chạy Watcher (dùng -m để Python giải quyết import app.* đúng)
nohup python -m app.watcher config.yaml > logs/watcher.log 2>&1 &
echo "✅ Watcher đã khởi động (PID: $!)"

# Chạy Telegram Bot
nohup python -m app.telegram_bot > logs/bot.log 2>&1 &
echo "✅ Telegram Bot đã khởi động (PID: $!)"

echo "📜 Logs: logs/watcher.log | logs/bot.log"
