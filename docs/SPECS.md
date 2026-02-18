# Specifications Chi Tiết — MedicalDocBot

Bảng specs theo **module**, bao gồm inputs/outputs, configs, error handling, perf targets, test cases liên kết usecase.
Dùng làm checklist "chậm nhưng chắc" khi implement từng phase.

---

## Module 1: Folder Structure & Taxonomy (V2)

| Thuộc tính | Specs |
|------------|-------|
| **Hierarchy** | `~/MedicalDevices/<category_slug>/<group_slug>/<device_slug>/<subtype>/` |
| **Ví dụ** | `chan_doan_hinh_anh/x_quang/x_quang_ge_optima_xr220_standard/tech/manual_vi.pdf` |
| **Subfolders chuẩn** | `info/` `tech/` `config/` `links/` `price/` `contracts/` `compare/` `other/` |
| **Metadata file** | `device.yaml` mỗi thiết bị (xem template bên dưới) |
| **Slug regex** | `^[a-z0-9]+(?:_[a-z0-9]+)*$` — bắt buộc cho tất cả slugs |
| **File naming** | `snake_case_<lang|version>.ext` — VD: `manual_vi_v2.pdf`, `config_bid_2026.xlsx` |
| **Ignore patterns** | `.DS_Store`, `*.tmp`, `._*`, `Thumbs.db`, `~$*` → log `logs/ignored_files.log` |
| **Perf** | List 1.000+ files < 1s |

**`device.yaml` template**:
```yaml
vendor: "GE Healthcare"
model: "Optima XR220"
category_id: "chan_doan_hinh_anh"
category_slug: "chan_doan_hinh_anh/x_quang"
risk_class: "C"          # A/B/C/D theo NĐ 98/2021
year: 2018
hs_code: "9022.12.00"
status: "Hoạt động"
power_kw: 50
weight_kg: 1200
aliases: ["GE XR220", "Optima XR220"]
links:
  fda: "https://www.accessdata.fda.gov/..."
files:
  ky_thuat: []
  bao_gia: []
  hop_dong: []
```

**Test cases**:
- [ ] Tạo 2 thiết bị mẫu bằng `seed_samples.sh` → verify folder tree đúng hierarchy
- [ ] Slug golden samples pass: `x_quang_ge_optima_xr220_standard`, `sieu_am_hitachi_arrietta_60_fulloption`
- [ ] Chạy `setup-folders.sh` 2 lần → không duplicate, không lỗi

---

## Module 2: openClaw Gateway + Channels

| Thuộc tính | Specs |
|------------|-------|
| **Platform** | openClaw Node.js daemon, port 18789 (Gateway WS) |
| **Install** | `npm install -g openclaw@latest && openclaw onboard --install-daemon` |
| **Channels** | Telegram (primary) — cấu hình qua `openclaw.json` |
| **Safety whitelist** | Chỉ đọc/ghi `~/MedicalDevices/`; cấm `sudo`, `rm -rf` |
| **Session memory** | Context 10 tin nhắn gần nhất per user |
| **Skills** | `file_classifier`, `stt_vietnamese`, `email_parser`, `telegram_handler` |
| **Health check** | `openclaw doctor` → verify daemon + channels |

**`~/.openclaw/openclaw.json` (minimal)**:
```json
{
  "agent": {
    "model": "anthropic/claude-opus-4",
    "workspace": "~/.openclaw/workspace"
  },
  "channels": {
    "telegram": {
      "token": "${TELEGRAM_BOT_TOKEN}",
      "dmPolicy": "pairing"
    }
  }
}
```

**Test cases**:
- [ ] `openclaw doctor` → no errors
- [ ] Telegram ping → bot reply (UC1 smoke test)
- [ ] Skill `file_classifier` → trả `doc_type` + `confidence`

---

## Module 3: File Watcher & Event Queue

| Thuộc tính | Specs |
|------------|-------|
| **Watch path** | Recursive `~/MedicalDevices/**` |
| **Exclude** | `.git/`, `extracted/`, `logs/`, `.DS_Store`, `*.tmp` |
| **Debounce** | 3 giây (tránh event storm khi copy file lớn) |
| **Event schema** | `{"event": "created", "path": "...", "size_bytes": 123456, "ts": "ISO8601", "sha256": "..."}` |
| **Log format** | JSON Lines (`logs/watcher.jsonl`), rotate daily |
| **Error handling** | Retry 3x với exponential backoff; dead letter: `logs/failed_events.jsonl` |
| **Perf** | Detect latency < 5s; xử lý 100 events/phút |

**Test cases**:
- [ ] Drop 1 file → log event đúng trong 5s
- [ ] Drop 10 files cùng lúc → debounce gom thành ≤ batch hợp lý, không spam bot
- [ ] File `.DS_Store` → bị ignore, không log event

---

## Module 4: Kreuzberg Extractor

| Thuộc tính | Specs |
|------------|-------|
| **Library** | `kreuzberg` Python (PyPI), Rust core, ARM64 macOS native |
| **API** | Async: `await extract_bytes(data, mime_type)` → `ExtractionResult` |
| **Output** | `{content: str, metadata: {pages, lang, title, author}, tables: [[...]]}` |
| **Formats** | PDF, DOCX, XLSX, images (OCR), HTML, email — 75+ formats |
| **Cache** | `extracted/<sha256>.json`, TTL 30 ngày |
| **Classify hints** | Keywords trong text: `manual/spec/config/bid/contract/award/fda/ce` |
| **Error handling** | Fallback plain text nếu structured extraction fail |
| **Perf** | PDF 10MB < 3s; batch 10 files < 20s |

**Test cases**:
- [ ] Extract `brochure.pdf` → `content` không rỗng, `metadata.lang` detect được
- [ ] Extract `spec.xlsx` → `tables` có dữ liệu
- [ ] Cache hit: extract lần 2 cùng file → không re-process (check `sha256`)

---

## Module 5: Classifier + Confirm Flow

| Thuộc tính | Specs |
|------------|-------|
| **Input signals** | Folder path + filename + 200 ký tự đầu extract + keywords |
| **Rule-based (fallback)** | `path ∋ /tech/` → `ky_thuat`; `path ∋ /price/ AND name ∋ bao_gia` → `bao_gia`; v.v. |
| **openClaw skill** | `file_classifier` → trả `{doc_type, confidence, reason}` |
| **Confidence threshold** | > 0.7 → auto-suggest; ≤ 0.7 → hỏi user chọn |
| **Telegram message** | _"📄 `manual_vi.pdf` (2MB) → GE XR220. Đoán: **ky_thuat** (85%). [✅ Đúng] [✏️ Sửa]"_ |
| **Timeout** | Không reply sau 5 phút → default `khac` + log warning |
| **Storage** | `index_store.py` SQLite upsert sau confirm |

**DOC_TYPE_RULES** (theo thứ tự ưu tiên):
```
path ∋ /tech/          → ky_thuat
path ∋ /config/        → cau_hinh
path ∋ /contracts/     → hop_dong
path ∋ /price/ AND name ∋ {bao_gia,quotation,quote} → bao_gia
path ∋ /price/ AND name ∋ {trung_thau,award}        → trung_thau
path ∋ /compare/       → so_sanh
path ∋ /other/         → khac
ambiguous              → hỏi user qua Telegram
```

**Test cases**:
- [ ] UC1 end-to-end: drop 5 files đúng folder → classify đúng 100%
- [ ] openClaw offline → rule-based fallback hoạt động
- [ ] Ambiguous file → bot hỏi confirm, user chọn → lưu đúng

---

## Module 6: Wiki Generator

| Thuộc tính | Specs |
|------------|-------|
| **Template** | `templates/model_template.md.j2` (Jinja2) |
| **Sections** | Thông số chính, Tài liệu (theo doc_type), Lịch sử cập nhật |
| **Idempotent** | So sánh hash section trước khi ghi; chỉ update section thay đổi |
| **Index files** | `wiki/index_categories.md`, `wiki/index_groups.md` — tự sinh |
| **Error handling** | Backup `.bak` trước khi ghi đè |
| **Perf** | Render 1 MD file < 1s |

**Model MD template (rút gọn)**:
```markdown
---
vendor: "{{vendor}}"
model: "{{model}}"
category_slug: "{{category_slug}}"
updated_at: "{{updated_at}}"
---

# {{model}} — {{vendor}}

## Thông số chính
| Thông số | Giá trị |
|----------|---------|
| Công suất | {{power_kw}} kW |
| Trọng lượng | {{weight_kg}} kg |
| Risk class | {{risk_class}} |

## Tài liệu
{% for doc_type, files in file_groups.items() %}
### {{doc_type_label[doc_type]}}
{% for f in files %}
- [{{f.name}}]({{f.rel_path}}) — {{f.size_human}} — {{f.updated_at}}
{% endfor %}
{% endfor %}

## Lịch sử cập nhật
<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->
| Ngày | File | Loại |
|------|------|------|
{% for entry in history %}
| {{entry.date}} | {{entry.name}} | {{entry.doc_type}} |
{% endfor %}
<!-- AUTO-GENERATED: END -->
```

**Test cases**:
- [ ] Chạy `wiki_generator.py` 2 lần → không có dòng duplicate
- [ ] Thêm 1 file mới → section đúng doc_type được cập nhật
- [ ] `wiki/index_categories.md` liệt kê đủ 25 categories

---

## Module 7: Paperless-ngx Integration *(Phase 2)*

| Thuộc tính | Specs |
|------------|-------|
| **Docker image** | `ghcr.io/paperless-ngx/paperless-ngx:latest`, port 8000 |
| **Auth** | `POST /api/token/` → `{"token": "abc..."}` → header `Authorization: Token abc...` |
| **Upload** | `POST /api/documents/post_document/` multipart + tags JSON |
| **Search** | `GET /api/documents/?query=<fulltext>&tags__name=<tag>` |
| **Tags scheme** | `device:<slug>`, `type:<doc_type>`, `lang:vi`, `status:confirmed` |
| **OCR language** | `PAPERLESS_OCR_LANGUAGE=vie+eng` |
| **Fallback** | Nếu offline → Kreuzberg extractor tự động |
| **Perf** | Upload 10MB PDF < 30s; search < 1s |

**Test cases**:
- [ ] `GET /api/documents/` → auth OK, trả list
- [ ] Upload 1 PDF → OCR text xuất hiện trong search
- [ ] Paperless offline → `extractor_kreuzberg.py` fallback hoạt động

---

## Module 8: Search Engine

| Thuộc tính | Specs |
|------------|-------|
| **Phase 2 MVP** | Paperless fulltext + SQLite index (doc_type + keyword + device_slug) |
| **Hierarchy parse** | "XQuang GE" → `category=chan_doan_hinh_anh`, `group=x_quang` |
| **Merge & rank** | Paperless score + recency + doc_type match |
| **Output** | Top 3 kết quả, inline keyboard Telegram |
| **Perf** | Search < 3s |

**Test cases**:
- [ ] UC2: `/find cấu hình chào giá XQuang GE` → ≥ 1 kết quả đúng
- [ ] UC3: `/send hop_dong mới nhất <slug>` → đúng file mới nhất
- [ ] Query không có kết quả → bot trả "Không tìm thấy, thử từ khác?"

---

## Non-Functional Specs

| Category | Target |
|----------|--------|
| **Storage** | Files raw: không giới hạn; SQLite index: < 100MB; Paperless: ~2GB/1.000 docs |
| **RAM (M4 24GB)** | openClaw: ~500MB; Paperless Docker: ~2GB; kreuzberg peak: ~500MB |
| **Uptime** | 24/7; watcher auto-restart; Docker `restart: unless-stopped` |
| **Backup** | `backup.py` tự động file > 10MB; log mọi thao tác |
| **Monitoring** | JSON logs rotate 7 ngày; `logs/` directory |
| **Security** | Local-only `127.0.0.1`; whitelist `~/MedicalDevices`; không `sudo` |
| **Idempotent** | Mọi script chạy lại → không duplicate, không lỗi |

---

## UC Coverage Matrix

| Module | UC1 | UC2 | UC3 | UC4 | UC5 | UC6 | UC7 | UC8 | UC9 | UC10 |
|--------|-----|-----|-----|-----|-----|-----|-----|-----|-----|------|
| Taxonomy/Folder | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| openClaw | ✅ | — | — | — | — | — | ✅ | ✅ | — | — |
| Watcher | ✅ | — | — | — | — | ✅ | — | ✅ | — | — |
| Kreuzberg | ✅ | ✅ | — | ✅ | — | — | — | ✅ | ✅ | — |
| Classifier | ✅ | — | — | — | — | — | — | ✅ | — | — |
| Wiki Generator | ✅ | — | — | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| Paperless | — | ✅ | ✅ | — | ✅ | — | — | — | — | — |
| Search | — | ✅ | ✅ | — | — | — | ✅ | — | ✅ | — |
