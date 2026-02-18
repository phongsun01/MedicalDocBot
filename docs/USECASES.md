# USECASES: MedicalDocBot — 10 Use Cases chi tiết (V2.0)

**Hierarchy**: Loại (Category) → Nhóm (Group) → Thiết bị (Device)
**Ví dụ**: `chan_doan_hinh_anh` → `x_quang` → `x_quang_ge_optima_xr220_standard`

> **Extractor**: [kreuzberg](https://github.com/kreuzberg-dev/kreuzberg) — Python library, Rust core, 75+ formats, ARM64 macOS native.

---

## UC1 — Thêm & Auto-Classify File Mới `[P0 · Phase 1+2]`

**Scenario**: User drop PDF manual vào folder device.

**Input**: Copy `manual_vi.pdf` vào:
```
~/MedicalDevices/chan_doan_hinh_anh/x_quang/x_quang_ge_optima_xr220_standard/tech/
```

**Flow**:
1. `watcher.py` detect sự kiện `created` (debounce 3s)
2. `extractor_kreuzberg.py` extract text + metadata → cache `extracted/<sha256>.json`
3. `classifier.py` → openClaw skill `file_classifier` (confidence > 0.7) → hoặc rule-based fallback (`path ∋ /tech/` → `ky_thuat`)
4. `telegram_bot.py` gửi confirm: _"File `manual_vi.pdf` → xếp loại `ky_thuat`? [✅ Đúng] [✏️ Sửa]"_
5. User confirm → `index_store.py` upsert → `wiki_generator.py` update `model_x_quang_ge_optima_xr220_standard.md`

**Output**:
```
✅ Đã update wiki.
📄 manual_vi.pdf → ky_thuat
📊 Total ky_thuat: 6 files
```

**Modules**: `watcher.py`, `extractor_kreuzberg.py`, `classifier.py`, `index_store.py`, `wiki_generator.py`, `telegram_bot.py`

---

## UC2 — Tìm Tài Liệu Theo Từ Khoá `[P0 · Phase 2]`

**Scenario**: User mobile cần tìm tài liệu nhanh.

**Input** (Telegram): `/find cấu hình chào giá XQuang GE`

**Flow**:
1. `search.py` parse query → detect hierarchy: `category=chan_doan_hinh_anh`, `group=x_quang`
2. Paperless-ngx fulltext search (nếu enabled) → merge kết quả
3. SQLite index search theo `doc_type=bao_gia` + keyword
4. Rank + trả top 3 kết quả với inline keyboard

**Output** (Telegram):
```
🔍 Kết quả tìm kiếm: "cấu hình chào giá XQuang GE"

1. bao_gia_ge_xr220_2025q4.pdf — GE Optima XR220 — 2025-10-15
2. config_ge_xr220_standard.pdf — cấu hình kỹ thuật — 2024-06-01
3. quote_ge_xr220_2024.xlsx — báo giá Excel — 2024-03-20

[📥 Gửi #1] [📥 Gửi #2] [📥 Gửi #3]
```

**Modules**: `search.py`, `paperless_client.py`, `index_store.py`, `telegram_bot.py`

---

## UC3 — Gửi Tài Liệu Mới Nhất `[P0 · Phase 2]`

**Scenario**: Ngoài văn phòng, cần gửi contract ngay.

**Input** (Telegram): `/send hop_dong mới nhất x_quang_ge_optima_xr220_standard`

**Flow**:
1. Parse: `doc_type=hop_dong`, `device_slug=x_quang_ge_optima_xr220_standard`
2. SQLite query: `SELECT * FROM files WHERE device_slug=? AND doc_type='hop_dong' ORDER BY updated_at DESC LIMIT 1`
3. Bot gửi file PDF trực tiếp qua Telegram

**Output**:
```
📎 hop_dong_ge_xr220_2026q1.pdf (8.2 MB)
📅 Ký: 2026-01-15 | 📁 x_quang_ge_optima_xr220_standard/contracts/
```

**Modules**: `search.py`, `index_store.py`, `telegram_bot.py`

---

## UC4 — So Sánh Báo Giá Thiết Bị `[P1 · Phase 3]`

**Scenario**: Đánh giá chào giá trước khi đấu thầu.

**Input** (Telegram): `So sánh báo giá GE XQuang vs Shimadzu XQuang`

**Flow**:
1. `compare.py` query `doc_type=bao_gia` cho cả 2 device slugs
2. `extractor_kreuzberg.py` parse Excel/PDF → extract bảng giá
3. Diff + gen `wiki/compare_ge_vs_shimadzu_x_quang_2026.md`

**Output**:
```
📊 So sánh báo giá — XQuang (2026)

| Hạng mục       | GE Optima XR220 | Shimadzu RADspeed |
|----------------|-----------------|-------------------|
| Giá thiết bị   | 450,000,000 đ   | 420,000,000 đ     |
| Bảo hành       | 24 tháng        | 18 tháng          |
| Xuất xứ        | Mỹ              | Nhật              |

📄 Lưu: wiki/compare_ge_vs_shimadzu_x_quang_2026.md
```

**Modules**: `compare.py`, `extractor_kreuzberg.py`, `wiki_generator.py`, `telegram_bot.py`

---

## UC5 — Thống Kê Hợp Đồng `[P1 · Phase 3]`

**Scenario**: Kiểm kê trước audit nội bộ.

**Input** (Telegram): `/stats contract >10MB chan_doan_hinh_anh`

**Flow**:
1. `reports.py` query SQLite: `WHERE category_slug='chan_doan_hinh_anh' AND doc_type='hop_dong' AND size_bytes > 10485760`
2. Tổng hợp + render MD report

**Output**:
```
📊 Thống kê hợp đồng > 10MB — Chẩn đoán hình ảnh
| Thiết bị              | Size  | Ngày ký    |
|-----------------------|-------|------------|
| x_quang_ge_optima_... | 15 MB | 2026-01-15 |
| ct_scanner_siemens_.. | 22 MB | 2025-11-03 |
| mri_philips_ingenia_. | 18 MB | 2025-08-20 |

Total: 3 files | Tổng: 55 MB
📄 Report: wiki/reports/stats_hop_dong_2026.md
```

**Modules**: `reports.py`, `index_store.py`, `telegram_bot.py`

---

## UC6 — Tự Động Backup & Alert `[P1 · Phase 3]`

**Scenario**: File contract mới lớn → cần backup ngay.

**Input**: Drop `hop_dong_ge_xr220_2026q2.pdf` (12 MB) vào folder.

**Flow**:
1. `watcher.py` detect → `classifier.py` → `hop_dong`
2. `backup.py`: file > 10MB → copy sang backup path + ghi log
3. `telegram_bot.py` gửi alert

**Output**:
```
⚠️ File lớn được backup tự động!
📎 hop_dong_ge_xr220_2026q2.pdf (12 MB)
📁 Device: x_quang_ge_optima_xr220_standard
💾 Backup: ~/MedicalDevices/.backup/2026-02-18/
```

**Modules**: `watcher.py`, `classifier.py`, `backup.py`, `telegram_bot.py`

---

## UC7 — Voice Query `[P2 · Phase 3]`

**Scenario**: Tay bận, hỏi nhanh bằng giọng nói.

**Input**: Gửi voice message Telegram: _"Siêu âm Siemens có chứng nhận FDA không?"_

**Flow**:
1. `voice_stt.py` nhận audio → gọi openClaw skill `stt_vietnamese` → text
2. `search.py` parse: `category=chan_doan_hinh_anh`, `group=sieu_am`, keyword=`FDA`
3. SQLite + Paperless search → trả kết quả

**Output**:
```
🎤 Nhận dạng: "Siêu âm Siemens có chứng nhận FDA không?"

📄 Tìm thấy: fda_cert_siemens_acuson_s2000.pdf
📅 Cấp: 2023-05-10 | ✅ Còn hiệu lực

Gửi file chứng nhận? [📥 Gửi] [🔍 Xem thêm]
```

**Modules**: `voice_stt.py`, `openclaw_client.py`, `search.py`, `telegram_bot.py`

---

## UC8 — Batch Import Từ Email `[P2 · Phase 3]`

**Scenario**: Import hàng loạt attachments từ email nhà cung cấp.

**Input** (Telegram): `Import email attachments invoices Q1 vào x_quang`

**Flow**:
1. `email_import.py` → openClaw skill `email_parser` → download attachments
2. Batch classify từng file → `watcher.py` pipeline
3. Paperless upload + index

**Output**:
```
📧 Import email hoàn tất!
✅ 8 files: 3 bao_gia, 4 ky_thuat, 1 hop_dong
📁 Device: x_quang_ge_optima_xr220_standard
📊 Wiki đã được cập nhật.
```

**Modules**: `email_import.py`, `openclaw_client.py`, `classifier.py`, `watcher.py`

---

## UC9 — Gợi Ý Thiết Bị Thay Thế `[P2 · Phase 3]`

**Scenario**: Contract thiết bị sắp hết hạn, cần tìm phương án thay thế.

**Input** (Telegram): `Gợi ý thay GE XQuang cũ hết contract`

**Flow**:
1. `predictive.py` parse contract dates từ `index_store`
2. Query `compare/` folder → rank theo giá/spec/thương hiệu
3. Trả top 3 gợi ý kèm link wiki compare

**Output**:
```
💡 Gợi ý thay thế GE Optima XR220 (hết hạn: 2026-06)

1. 🥇 Shimadzu RADspeed — giá thấp hơn 7%, FDA OK
2. 🥈 Siemens Multix — tương đương spec, bảo hành 24th
3. 🥉 Philips DigitalDiagnost — cao cấp hơn, +15% giá

📄 So sánh chi tiết: wiki/compare/x_quang_alternatives_2026.md
```

**Modules**: `predictive.py`, `compare.py`, `index_store.py`, `telegram_bot.py`

---

## UC10 — Multi-User Audit Report `[P2 · Phase 3]`

**Scenario**: Team cần xem báo cáo kiểm kê, không chỉnh sửa được.

**Input** (Telegram): `Xuất audit report XQuang tháng 2/2026`

**Flow**:
1. `audit.py` query audit log → tổng hợp hoạt động theo user/thời gian
2. Render read-only MD report
3. Export PDF (optional) + gửi link

**Output**:
```
📋 Audit Report — XQuang — 02/2026

| Thời gian  | User  | Hành động          | File                    |
|------------|-------|--------------------|-------------------------|
| 2026-02-15 | phong | classify → ky_thuat | manual_ge_xr220_vi.pdf  |
| 2026-02-16 | phong | send → hop_dong    | contract_ge_2026q1.pdf  |
| 2026-02-18 | admin | import email (8)   | batch_q1_invoices       |

Total: 12 actions | 3 users
📄 Report: wiki/reports/audit_x_quang_2026_02.md (read-only)
```

**Modules**: `audit.py`, `index_store.py`, `telegram_bot.py`

---

## Coverage Summary

| UC | Mô tả | Priority | Phase | Status |
|----|-------|----------|-------|--------|
| UC1 | Auto-classify file mới | P0 | 1+2 | 🔲 |
| UC2 | Tìm tài liệu theo từ khoá | P0 | 2 | 🔲 |
| UC3 | Gửi tài liệu mới nhất | P0 | 2 | 🔲 |
| UC4 | So sánh báo giá | P1 | 3 | 🔲 |
| UC5 | Thống kê hợp đồng | P1 | 3 | 🔲 |
| UC6 | Backup & alert tự động | P1 | 3 | 🔲 |
| UC7 | Voice query STT | P2 | 3 | 🔲 |
| UC8 | Batch import email | P2 | 3 | 🔲 |
| UC9 | Predictive gợi ý | P2 | 3 | 🔲 |
| UC10 | Multi-user audit | P2 | 3 | 🔲 |

> **Ưu tiên test**: UC1 → UC2 → UC3 (Phase Gate 2). Các UC còn lại implement dần trong Phase 3.
