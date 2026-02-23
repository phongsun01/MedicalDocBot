@echo off
:: stop.bat - Dừng MedicalDocBot trên Windows
title MedicalDocBot - Stopper

echo 🛑 Đang dừng MedicalDocBot...

:: Tìm và đóng các tiến trình python đang chạy file cụ thể
:: Lưu ý: taskkill theo tên file có thể hơi khó trên Windows, thường sẽ tắt tất cả python
:: Nhưng ta sẽ cố gắng lọc theo command line nếu được

taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq MedicalDocBot*" >nul 2>nul
taskkill /F /IM python.exe /T >nul 2>nul

echo ✅ Đã gửi lệnh dừng các tiến trình Python.
echo ℹ️ Nếu bạn có các ứng dụng Python khác đang chạy, chúng cũng có thể bị ảnh hưởng.
pause
