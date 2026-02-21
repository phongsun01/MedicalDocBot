# Hướng dẫn Cấu hình Custom Model cho openClaw 2026

Tài liệu này hướng dẫn cách thêm một **Custom Provider (chuẩn OpenAI-compatible)** vào openClaw phiên bản mới nhất (2026.x).

> ⚠️ **Lưu ý bản 2026:** openClaw không còn hỗ trợ mục `"providers"` trong `openclaw.json` nữa. Toàn bộ việc cấu hình custom model được thực hiện hoàn toàn qua lệnh `models auth` và `models aliases`.

---

## Bước 1: Thêm Auth Profile (API Key & Base URL)

```bash
openclaw models auth add
```

Trả lời các câu hỏi tương tác:

| Câu hỏi | Trả lời |
|---|---|
| Token provider | `custom (type provider id)` |
| Provider id | `https://simpleverse.io.vn/route/v1` |
| Token method | `paste token` |
| Profile id | `simpleverse` (hoặc tên tuỳ chọn) |
| Does this token expire? | `No` |
| Paste token | Dán API Key vào (`sk-xxxx...`) |

---

## Bước 2: Tạo Alias (Gắn tên gọi với model)

Trong bản 2026, alias phải dùng **URL đầy đủ của provider** thay vì chỉ tên profile.

**Cú pháp đúng:**
```bash
openclaw models aliases add <tên-bí-danh> <base-url>/<tên-mã-model-gốc>
```

**Ví dụ thực tế với SimpleVerse + q-qwen3-coder-flash:**
```bash
openclaw models aliases add qwen-coder https://simpleverse.io.vn/route/v1/q-qwen3-coder-flash
```

> **Lưu ý:** Phải dùng URL đầy đủ (có `https://`), không phải tên profile ngắn như `simpleverse/q-qwen3-coder-flash`.

---

## Bước 3: Đặt Model làm Mặc định

```bash
openclaw models set qwen-coder
```

Kiểm tra lại toàn bộ cấu hình:
```bash
openclaw models status
```

---

## Bước 4: Test kết nối

Vì lệnh `eval` đã bị gỡ bỏ trong bản 2026, bạn dùng lệnh `agent` để test:

```bash
openclaw agent --to test --message "Xin chào, bạn tên là gì?"
```

Nếu model trả lời được = **Cấu hình thành công** ✅

---

### Mẹo: Quản lý Aliases & Cấu hình

```bash
# Xem danh sách aliases đã tạo
openclaw models aliases list

# Xoá một alias
openclaw models aliases remove qwen-coder

# Sửa cấu hình bị lỗi tự động
openclaw doctor --fix
```

### Thư mục cấu hình

| File | Nội dung |
|---|---|
| `~/.openclaw/openclaw.json` | Cấu hình chính (Telegram, Gateway, Aliases) |
| `~/.openclaw/agents/main/agent/auth-profiles.json` | API Keys đã lưu |
| `~/.openclaw/agents/main/agent/auth.json` | Thông tin Auth hiện tại |
