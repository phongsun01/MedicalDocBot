# Hướng dẫn Quản lý Telegram Bot

Tài liệu này hướng dẫn cách tùy biến Bot `@MedDocVn_Bot` và tích hợp vào nhóm chat.

## 1. Cách đổi tên và ảnh đại diện Bot

Để bot trông chuyên nghiệp hơn, bạn có thể đổi tên hiển thị (Name) và ảnh (Userpic).

1.  Mở Telegram, tìm bot **@BotFather** (có tích xanh).
2.  Gõ lệnh `/mybots`.
3.  Chọn bot của bạn từ danh sách (@MedDocVn_Bot).
4.  Chọn **Edit Bot**.
5.  Chọn mục cần sửa:
    -   **Edit Name**: Đổi tên hiển thị (VD: "MedicalDoc Assistant").
    -   **Edit Description**: Đổi mô tả khi người dùng mới vào bot.
    -   **Edit Botpic**: Gửi một bức ảnh để làm avatar cho bot.

## 2. Cách tạo nhóm chat với Bot

Để bot gửi thông báo vào một nhóm chung (thay vì nhắn riêng cho bạn):

1.  **Tạo nhóm mới** trên Telegram (hoặc dùng nhóm có sẵn).
2.  **Thêm Bot vào nhóm**:
    -   Vào cài đặt nhóm > Add Members.
    -   Tìm `@MedDocVn_Bot` và thêm vào.
3.  **Lấy Chat ID của nhóm**:
    -   Thêm bot **@RawDataBot** vào nhóm đó.
    -   Nó sẽ hiện ra một đoạn JSON. Tìm dòng `"chat": { "id": -100xxxxxxxx, ... }`.
    -   Copy số ID đó (bao gồm cả dấu âm `-`).
    -   Sau khi lấy được ID, bạn có thể kick @RawDataBot ra khỏi nhóm.
4.  **Cập nhật cấu hình**:
    -   Mở file `app/process_event.py`.
    -   Tìm dòng `target = "..."`.
    -   Thay ID cá nhân bằng ID nhóm vừa lấy.
    -   Khởi động lại Watcher.
