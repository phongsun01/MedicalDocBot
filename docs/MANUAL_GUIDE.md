# Hướng dẫn copy file trực tiếp (Manual Copy) 📂

Ngoài việc thả file vào thư mục gốc để Bot tự phân loại, bạn có thể copy file **thẳng vào thư mục thiết bị** nếu đã biết rõ nó thuộc về đâu. Bot sẽ tự động nhận diện và cập nhật Wiki mà không cần hỏi lại bạn trên Telegram.

## 1. Cấu trúc thư mục chuẩn
Để Bot có thể nhận diện tự động, bạn cần copy file vào đúng cấp độ thư mục thứ 4 (Doc Type folder).

Cấu trúc: `MedicalDevices / [Danh mục] / [Nhóm] / [Thiết bị] / [Loại tài liệu] / file.pdf`

Ví dụ: 
`MedicalDevices/chan_doan_hinh_anh/x_quang/ge_optima_xr220/tech/manual_user.pdf`

## 2. Các thư mục loại tài liệu (Doc Type) được hỗ trợ:
Bạn phải copy vào một trong các thư mục con sau của thiết bị:
- `tech/`: Tài liệu kỹ thuật (`ky_thuat`)
- `config/`: Cấu hình (`cau_hinh`)
- `price/`: Báo giá (`bao_gia`)
- `contracts/`: Hợp đồng (`hop_dong`)
- `compare/`: So sánh (`so_sanh`)
- `info/`: Thông tin chung (`thong_tin`)
- `links/`: Liên kết (`lien_ket`)
- `other/`: Khác (`khac`)

## 3. Lợi ích khi copy trực tiếp:
- **Tốc độ**: Bot sẽ bỏ qua bước gọi AI (Gemini) để phân loại.
- **Tiết kiệm**: Không tốn token/hạn ngạch API.
- **Tự động**: Bot sẽ coi như dữ liệu đã "Phê duyệt" (Confirmed) và cập nhật ngay vào database cũng như Wiki Obsidian của bạn.

---
*Lưu ý: Nếu bạn copy vào thư mục gốc hoặc các thư mục không đúng cấu trúc 5 cấp, Bot vẫn sẽ gọi AI để hỗ trợ bạn phân loại như bình thường.*
