# Hướng dẫn Xử lý Thủ công & Feedback Loop

Mặc dù Gemini AI có độ chính xác cao, đôi khi vẫn có sai sót. Đây là quy trình xử lý chuẩn.

## 1. Khi AI phân loại sai (Wrong Classification)

**Tình huống**: File là "Báo giá" nhưng AI nhận diện là "Kỹ thuật".

### Cách 1: Sửa thủ công (Nhanh nhất)
1.  **Di chuyển file**: Kéo file từ folder sai sang folder đúng trong `~/MedicalDevices`.
    -   VD: Từ `Tim mach/Ky thuat/` sang `Tim mach/Bao gia/`.
2.  **Watcher tự động**: Hệ thống sẽ phát hiện file bị di chuyển -> Cập nhật lại Database & Wiki.

### Cách 2: Feedback để AI học (Cải thiện lâu dài)
1.  **Gửi file cho Admin (Dev)**: Gửi file `logs/classifier.log` để Dev xem tại sao sai.
2.  **Điều chỉnh Prompt**: Dev sẽ thêm "keyword" đặc thù của file đó vào `classifier.py` hoặc `config.yaml` để lần sau không sai nữa.

## 2. Khi AI không tìm thấy thiết bị (Unknown Model)

**Tình huống**: File thuộc model mới chưa có trong file `data/taxonomy.yaml`.

### Quy trình:
1.  **Cập nhật Taxonomy**:
    -   Mở file `data/taxonomy.yaml`.
    -   Thêm một mục mới vào dưới nhóm tương ứng.
    ```yaml
     - slug: "model_moi"
       label_vi: "Model Mới ABCD"
       vendor: "Hãng X"
    ```
2.  **Chạy lại xử lý**:
    -   Kéo file ra ngoài rồi thả lại vào folder `~/MedicalDevices`.
    -   Hệ thống sẽ quét lại và nhận diện đúng model mới.

## 3. Cách đưa trang Index lên đầu

**Obsidian / File Explorer**:
-   Theo mặc định, máy tính sắp xếp theo tên (Alphabet).
-   Để Index luôn ở đầu, tôi đã đặt tên là `00_Danh_muc_thiet_bi.md` (số 00 giúp nó luôn đứng top).
-   Trong các thư mục con, file `Index.md` có thể bị trôi.
-   **Mẹo**: Đổi tên thành `!Index.md` hoặc `_Index.md` nếu bạn muốn nó nổi bật hơn nữa.
