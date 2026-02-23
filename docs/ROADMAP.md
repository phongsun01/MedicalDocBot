# Roadmap: MedicalDocBot — "Chậm nhưng chắc" (Taxonomy V2)

Chiến lược 3 tầng: **Core (nền tảng)** → **MVP (3 UC P0)** → **Nâng cao (OCR/DMS/semantic/voice/stats)**.
Paperless-ngx để sau MVP vì thêm Docker stack + vận hành; khi pipeline ổn thì API rất mạnh.

---

## Phase 0 — Core nền tảng *(Tuần 1)*

**Mục tiêu**: File vào đúng nơi, wiki sinh đúng cấu trúc, bot chạy 24/7, không hỏng.
Chưa cần OCR, Paperless, hay semantic search.

### 0.1 Chuẩn hóa taxonomy & thư mục (V2) *(Hoàn thành)*

- Quy ước slug `snake_case`: `chan_doan_hinh_anh/x_quang/x_quang_ge_optima_xr220_standard/`
- Subfolders chuẩn mỗi device: `info/` `tech/` `config/` `links/` `price/` `contracts/` `compare/` `other/`
- `device.yaml` tối thiểu: `vendor`, `model`, `category_slug`, `risk_class`, `aliases`
- Script `setup-folders.sh` (bash) sinh cây 125+ folders từ `data/taxonomy.yaml` V2

**Deliverable D0a**: 2 "golden sample" devices:
- `x_quang_ge_optima_xr220_standard`
- `sieu_am_hitachi_arrietta_60_fulloption`

### 0.2 Wiki template *(Hoàn thành)*

- Template `templates/model_template.md.j2` (Jinja2): bảng tóm tắt + sections theo doc_type
- `wiki/index_categories.md` + `wiki/index_groups.md` tự sinh
- Link file: relative path từ wiki → device folder

**Deliverable D0b**: Mở wiki → click Loại → Nhóm → Thiết bị → thấy trang với sections rỗng sẵn.

### 0.3 openClaw 24/7 + Telegram *(Phase 2.1 - Current)*

- Cài openClaw: `npm install -g openclaw@latest && openclaw onboard --install-daemon`
- Bật kênh Telegram, cấu hình `~/.openclaw/openclaw.json`
- Whitelist path `~/MedicalDevices/`, cấm lệnh phá hoại
- Skills: `file_classifier`, `stt_vietnamese`, `email_parser`

**Deliverable D0c**: Nhắn "ping" → bot trả lời; bot đọc được danh sách thiết bị từ folder.

### 0.4 Watcher + event queue *(1–2 ngày)*

- `watcher.py` theo dõi `~/MedicalDevices/**` (recursive), debounce 3s
- Event schema: `{"event": "created", "path": "...", "size_bytes": N, "ts": "ISO8601", "sha256": "..."}`
- Ignore: `.DS_Store`, `*.tmp`, `._*`, `Thumbs.db`
- Log JSON Lines: `logs/watcher.jsonl`

**Deliverable D1a**: Thả 5 file vào nhiều subfolder → bot báo 1 message tổng hợp, không spam.

### 0.5 Kreuzberg extraction baseline *(1–2 ngày)*

- `extractor_kreuzberg.py`: async extract text/metadata/tables → cache `extracted/<sha256>.json`
- "Candidate signals": ngôn ngữ (VI/EN), keywords (`manual/spec/bid/contract/award/fda/ce`)
- Chưa auto-classify, chỉ preview

**Deliverable D1b**: Bot reply "đã đọc được nội dung" + vài dòng preview.

**Phase Gate 0** ✓: watcher ổn định + bot 24/7 + wiki template chuẩn + extract không lỗi.

---

## Phase 1 — MVP *(Hoàn thành)*

**Mục tiêu**: Hoàn thành 3 UC P0 — **(UC1) thêm file → classify → wiki update**, **(UC2) tìm kiếm**, **(UC3) gửi file**.
Chưa cần Paperless.

### 1.1 Auto-classify + confirm flow *(✅ Hoàn thành — v2.5.0)*

- `classifier.py`: AI via 9router local gateway → confidence score (0.0–1.0) từ model
- **Mọi file** (kể cả confidence cao) → lưu DRAFT `confirmed=False` → bot gửi message với nút **✅ Phê duyệt** / **✏️ Chỉnh sửa**
- Sau người dùng bấm approve: file mới được di chuyển + wiki mới được cập nhật  
- Các bug quan trọng đã fix: Telegram HTML mode, `doc_type` multi-filter search, encapsulation `get_file_by_id`, rate-limit configurable

**Deliverable**: Thêm 1 file → bot hỏi với nút → bấm Phê duyệt → nhãn lưu + wiki cập nhật. ✅

### 1.2 Wiki auto-update *(2–3 ngày)*

- `wiki_generator.py`: sau confirm → chèn link vào đúng section `Device.md`
- Bảng tóm tắt: tự cập nhật `count`, `latest`, phân tách VI/EN
- Idempotent: chạy lại không tạo dòng trùng

**Deliverable D2**: UC1 end-to-end — drop file → confirm → MD update + table refresh.

### 1.3 Search qua bot *(1–2 ngày)*

- `search.py`: parse hierarchy (Loại/Nhóm/Device) + doc_type + keyword
- SQLite index search + Kreuzberg full-text
- Output: top 3 kết quả + inline keyboard `[📥 Gửi #1] [📥 Gửi #2] [📥 Gửi #3]`

**Deliverable D3a**: UC2 — `/find cấu hình chào giá XQuang GE` → ≥ 1 kết quả đúng.

### 1.4 Send file *(0.5–1 ngày)*

- Bot gửi file trực tiếp qua Telegram (< 50MB) hoặc trả path + hướng dẫn
- Query: `SELECT * FROM files WHERE device_slug=? AND doc_type=? ORDER BY updated_at DESC LIMIT 1`

**Deliverable D3b**: UC3 — `/send hop_dong mới nhất x_quang_ge_optima_xr220_standard` → đúng file.

**Phase Gate 1** ✓: 3 UC P0 chạy ổn với ~50–100 files, không cần sửa tay wiki.

---

## Phase 2 — Nâng cao *(Tuần 3–4 - In Progress)*

**Mục tiêu**: Thêm Paperless-ngx OCR/index mạnh, rồi semantic/compare/stats/voice.

### 2.1 Triển khai Paperless-ngx *(2–3 ngày)*

- Docker Compose: `ghcr.io/paperless-ngx/paperless-ngx:latest`, port 8000
- `PAPERLESS_OCR_LANGUAGE=vie+eng`, `PAPERLESS_TIME_ZONE=Asia/Ho_Chi_Minh`
- Lấy token: `POST /api/token/` → `Authorization: Token <token>`
- `paperless_client.py`: upload, search, tag

**Deliverable**: Mở web Paperless, upload 10 PDF scan, thấy OCR text.

### 2.2 Sync watcher → Paperless *(2–4 ngày)*

- Auto upload PDF/scan qua `POST /api/documents/post_document/`
- Tags: `device:<slug>`, `type:<doc_type>`, `lang:vi`, `status:confirmed`
- Search: `GET /api/documents/?query=...` → full-text + highlights
- Fallback: nếu Paperless offline → Kreuzberg extractor

**Deliverable**: Query "manual Siemens" → kết quả từ Paperless kèm highlights.

### 2.3 Wiki embed Paperless *(1–2 ngày)*

- `Device.md`: thêm section "Paperless documents" (ID/Title/Created + link web)
- File gốc vẫn local; Paperless là lớp index/OCR (có thể trỏ storage cùng volume)

### 2.4 Semantic search *(optional, sau khi Paperless ổn)*

- RAG: Paperless top-k + Kreuzberg extract → trả lời qua openClaw LLM
- Hỏi: "thiết bị nào có FDA và giá < X?" → danh sách + link bằng chứng

### 2.5 UC P1/P2 *(Tuần 4+)*

| UC | Module | Mô tả |
|----|--------|--------|
| UC4 | `compare.py` | So sánh báo giá GE vs Shimadzu → MD compare |
| UC5 | `reports.py` | Stats contract > 10MB → bảng + MD report |
| UC6 | `backup.py` | File > 10MB → backup + Telegram alert |
| UC7 | `voice_stt.py` | Voice → openClaw STT → search |
| UC8 | `email_import.py` | Email attachments → watcher pipeline |
| UC9 | `predictive.py` | Gợi ý thiết bị thay thế |
| UC10 | `audit.py` | Multi-user audit log + read-only report |

---

## Lịch làm việc (gợi ý)

| Tuần | Ngày | Việc |
|------|------|------|
| **Tuần 1** | 1–2 | Taxonomy V2 + folder + `seed_samples.sh` |
| | 3 | openClaw 24/7 + Telegram + whitelist |
| | 4–5 | Watcher + event queue + chống spam |
| | 6–7 | Kreuzberg baseline extract + cache JSON |
| **Tuần 2** | 8–9 | Classifier + confirm flow |
| | 10–11 | Wiki generator + table auto-update + idempotent |
| | 12 | Search basic (device/type/keyword) |
| | 13–14 | Send file + hardening + test 100 files |
| **Tuần 3** | 15–17 | Paperless Docker + token + upload + API search |
| | 18–19 | Sync tag + embed wiki |
| **Tuần 4** | 20–21 | Semantic search (optional) |
| | 22–28 | Compare, stats, voice, email, audit |

---

## Deliverables Checklist

| ID | Deliverable | Phase | Status |
|----|-------------|-------|--------|
| D0a | Golden sample 2 thiết bị + folder tree đúng | 0 | 🔲 |
| D0b | Wiki template chuẩn, click được Loại→Nhóm→Device | 0 | 🔲 |
| D0c | Bot 24/7, Telegram ping/pong | 0 | 🔲 |
| D1a | Watcher không spam, debounce 3s | 0 | 🔲 |
| D1b | Kreuzberg extract + preview qua bot | 0 | 🔲 |
| D2 | UC1: drop file → confirm → wiki update tự động | 1 | 🔲 |
| D3a | UC2: search basic + top 3 kết quả | 1 | ✅ |
| D3b | UC3: gửi file đúng qua Telegram | 1 | ✅ |
| D4 | Paperless chạy ổn + OCR + API query/highlights | 2 | 🔲 |
| D5 | Hybrid search + compare/stats/voice | 2 | 🔲 |
