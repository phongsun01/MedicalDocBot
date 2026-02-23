# Hướng dẫn chạy MedicalDocBot 🚀

Tài liệu này hướng dẫn bạn cách khởi động và dừng hệ thống MedicalDocBot (bao gồm Watcher theo dõi thư mục và Telegram Bot) sau khi bạn bật máy tính.

## 1. Đối với macOS (Máy tính hiện tại của bạn)

Bạn có thể sử dụng các script `.sh` đã được chuẩn bị sẵn trong thư mục gốc của dự án.

### Khởi động Bot
Mở Terminal, di chuyển vào thư mục dự án và chạy:
```bash
./start.sh
```
*Script này sẽ tự động kích hoạt môi trường ảo `.venv`, thiết lập PYTHONPATH và chạy Bot dưới nền (background).*

### Dừng Bot
Khi bạn muốn tắt Bot trước khi tắt máy:
```bash
./stop.sh
```

### Kiểm tra Logs (Xem Bot đang làm gì)
Logs được lưu trong thư mục `logs/`:
- `logs/bot.log`: Nhật ký hoạt động của Telegram Bot.
- `logs/watcher.log`: Nhật ký hoạt động của Watcher (theo dõi file mới).

Bạn có thể xem trực tiếp bằng lệnh:
```bash
tail -f logs/bot.log
```

---

## 2. Đối với Windows (Nếu bạn cài sang máy khác)

Sử dụng các file `.bat`:

- **Khởi động**: Click đúp vào file `start.bat`.
- **Dừng**: Click đúp vào file `stop.bat`.

---

## 3. Lưu ý quan trọng
- **Môi trường ảo**: Các script trên giả định bạn đã có thư mục `.venv`. Nếu chưa có, hãy chạy `python -m venv .venv` và cài đặt dependencies trước.
- **Quyền thực thi**: Nếu trên macOS báo lỗi "Permission denied" khi chạy `.sh`, hãy cấp quyền bằng lệnh:
  ```bash
  chmod +x start.sh stop.sh
  ```
- **Tắt máy**: Trước khi tắt máy, bạn nên chạy `./stop.sh` để đảm bảo các tiến trình được đóng sạch sẽ, tránh lỗi xung đột cổng/session khi bật lại.
