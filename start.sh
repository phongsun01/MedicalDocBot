#!/bin/bash
# start.sh - Khởi động MedicalDocBot (Watcher & Telegram Bot)

# Load biến môi trường nếu cần
source .venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.

# Tạo thư mục logs nếu chưa có
mkdir -p logs

echo "🚀 Đang khởi động MedicalDocBot..."

# Kiểm tra xem bot có đang chạy không
if pgrep -f "app/watcher.py" > /dev/null; then
    echo "⚠️  Watcher đang chạy. Đang khởi động lại..."
    pkill -f "app/watcher.py"
fi

if pgrep -f "app/telegram_bot.py" > /dev/null; then
    echo "⚠️  Telegram Bot đang chạy. Đang khởi động lại..."
    pkill -f "app/telegram_bot.py"
fi

# Chạy Watcher
nohup python app/watcher.py > logs/watcher.log 2>&1 &
echo "✅ Watcher đã khởi động (PID: $!)"

# Chạy Telegram Bot
nohup python app/telegram_bot.py > logs/bot.log 2>&1 &
echo "✅ Telegram Bot đã khởi động (PID: $!)"

echo "📜 Logs đang được ghi vào thư mục logs/."
