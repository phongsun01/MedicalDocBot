@echo off
:: start.bat - Khởi động MedicalDocBot trên Windows
title MedicalDocBot - Starter

echo 🚀 Đang khởi động MedicalDocBot...

:: Kiểm tra Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ Không tìm thấy Python. Vui lòng cài đặt Python.
    pause
    exit /b
)

:: Kích hoạt môi trường ảo nếu có
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

:: Thiết lập PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%

:: Tạo thư mục logs
if not exist logs mkdir logs

:: Khởi động con hổ
echo 📂 Khởi động Watcher...
start /b python app/watcher.py > logs/watcher.log 2>&1
echo 🤖 Khởi động Telegram Bot...
start /b python app/telegram_bot.py > logs/bot.log 2>&1

echo ✅ Đã khởi động xong!
echo 📜 Logs được lưu tại thư mục logs/
pause
