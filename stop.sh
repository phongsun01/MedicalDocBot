#!/bin/bash
# stop.sh - Dừng MedicalDocBot (Watcher & Telegram Bot)

echo "🛑 Đang dừng MedicalDocBot..."

# Tìm và đóng watcher
if pgrep -f "app/watcher.py" > /dev/null; then
    pkill -f "app/watcher.py"
    echo "✅ Đã đóng Watcher."
else
    echo "ℹ️ Watcher đang không chạy."
fi

# Tìm và đóng telegram bot
if pgrep -f "app/telegram_bot.py" > /dev/null; then
    pkill -f "app/telegram_bot.py"
    echo "✅ Đã đóng Telegram Bot."
else
    echo "ℹ️ Telegram Bot đang không chạy."
fi

echo "🏁 Hoàn tất."
