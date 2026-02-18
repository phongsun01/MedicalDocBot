# PRD: MedicalDocBot — Hệ thống Wiki + Bot Quản lý Tài liệu Thiết bị Y tế

**Version:** 1.1 | **Date:** 18/02/2026 | **Owner:** Phong | **Target:** Mac Mini M4 24GB, self-hosted 24/7

---

## 1. Tổng quan & Mục tiêu

### Vấn đề
Explorer/folder thủ công mất thời gian tìm spec/contract/giá thiết bị y tế (PDF/DOC/Excel, tiếng Việt/Anh/scan).

### Giải pháp
Hệ thống DMS hybrid chạy **100% local**:
- **Kreuzberg** extract text/metadata từ PDF, DOCX, Excel
- **SQLite** index + SHA-256 dedup
- **Wiki Markdown** auto-update theo từng thiết bị
- **Telegram Bot** (Python) search semantic/chat mobile, auto-classify, update wiki

### KPI Mục tiêu

| Chỉ số | Mục tiêu |
|---|---|
| Tìm tài liệu | < 5 giây |
| Accuracy classify | > 90% |
| Scale | 1.000+ thiết bị, 10.000+ files |
| Bảo mật | 100% local, không upload cloud |

### Hierarchy Thiết bị

```
Danh mục (Category) → Nhóm (Group) → Thiết bị (Device)

01_chan_doan_hinh_anh/
├── x_quang/
│   ├── x_quang_ge_optima_xr220_standard/
│   └── x_quang_shimadzu_mobiledart_neo/
└── sieu_am/
    ├── sieu_am_siemens_acuson_s2000/
    └── sieu_am_hitachi_arrietta_60_fulloption/

17_kiem_soat_nhiem_khuan/
└── autoclave/
    └── autoclave_getinge_gs3_series/
```

> Taxonomy đầy đủ 25 nhóm theo **TT 30/2015/TT-BYT + NĐ 98/2021/NĐ-CP** — xem `data/taxonomy.yaml`

---

## 2. User Stories & Requirements

### 2.1 Core Flows

| ID | Actor | Story | Priority |
|---|---|---|---|
| US1 | User | Thêm file PDF/Excel vào folder thiết bị → bot Telegram gợi ý classify "ky_thuat / hop_dong / bao_gia?" → confirm → update wiki MD + count | **P0** |
| US2 | User (mobile) | Chat Telegram: "Tìm cấu hình chào giá XQuang GE" → danh sách kết quả + gửi PDF | **P0** |
| US3 | User | "Gửi hợp đồng mới nhất x_quang_ge_optima_xr220_standard" → bot gửi đúng file mới nhất trong `/contracts/` | **P0** |
| US4 | User | "So sánh giá DeviceA vs DeviceB Siêu âm" → bảng extract từ Excel + lưu MD mới | **P1** |
| US5 | Admin | "Stats: Số contract >10MB loại Chẩn đoán hình ảnh" → bảng + MD report | **P1** |
| US6 | User | File mới >10MB → backup tự động + Telegram alert | **P1** |
| US7 | User | Voice: "Siêu âm Siemens FDA?" → STT → search → trả kết quả | **P2** |
| US8 | User | Batch import từ email attachments → pipeline watcher | **P2** |
| US9 | User | Gợi ý thiết bị thay thế (heuristic) | **P2** |
| US10 | Admin | Audit report / read-only share | **P2** |

### 2.2 Non-Functional Requirements

| Yêu cầu | Mục tiêu |
|---|---|
| Performance | Extract batch 100 files < 2 phút, search < 3 giây |
| Storage | Files raw + DB index < 10GB ban đầu |
| Uptime | 24/7, daemon tự restart khi crash |
| Security | Local-only, whitelist path `~/MedicalDevices`, approve thủ công lệnh nhạy |
| Idempotent | Mọi script chạy lại không tạo duplicate |
| Error handling | try/except + JSON log, không crash daemon |

---

## 3. System Design

```
┌─────────────────────┐    watchdog    ┌──────────────────────┐
│   ~/MedicalDevices  │ ─────────────▶ │   watcher.py         │
│  Loại/Nhóm/Device   │   (debounce    │   (Python daemon)    │
│  tech/contracts/... │    3 giây)     └──────────┬───────────┘
└─────────────────────┘                           │
                                                  │ event queue
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                    ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
                    │ classifier.py│   │index_store.py│   │wiki_generator.py │
                    │ (rule-first) │   │ (SQLite WAL) │   │ (Jinja2 + marker)│
                    └──────┬───────┘   └──────────────┘   └──────────────────┘
                           │ ambiguous
                           ▼
                  ┌─────────────────┐
                  │ telegram_bot.py │ ◀── User chat (mobile 24/7)
                  │ /find /send     │
                  └────────┬────────┘
                           │
                  ┌────────┴────────┐
                  │   search.py     │
                  │ (SQLite FTS5 +  │
                  │  taxonomy-aware)│
                  └─────────────────┘

[Phase 3 — hook sẵn]
  extractor_kreuzberg.py → cache extracted/<sha256>.json
  Ollama + ChromaDB       → semantic search
  Paperless-ngx           → OCR/tag (Token auth)
```

**Data Flow:**
```
File mới → watcher (debounce 3s) → sha256 dedup → classifier (rule-first)
         → [confirm Telegram nếu ambiguous] → index SQLite → wiki MD update
         → [extractor cache] → search index
```

---

## 4. Modules & Tasks

### Module 1: Storage & Hierarchy *(Phase 1 — Core)*

**Yêu cầu:** Cây thư mục chuẩn, slug validate, device.yaml metadata.

- [x] `scripts/setup_taxonomy_folders.sh` — sinh cây 25 nhóm idempotent
- [x] `app/slug.py` — validate regex `^[a-z0-9]+(?:_[a-z0-9]+)*$` + normalize tiếng Việt
- [x] `templates/device_yaml_template.yaml.j2` — metadata thiết bị
- [x] `app/create_device.py` — tạo device folder + device.yaml + wiki MD

### Module 2: Watcher + Index *(Phase 1 — Core)*

**Yêu cầu:** Phát hiện file mới, dedup SHA-256, log JSON.

- [x] `app/watcher.py` — watchdog + debounce 3s + event queue
- [x] `app/index_store.py` — SQLite WAL, upsert sha256, pending_classification
- [x] `app/taxonomy.py` — parse taxonomy YAML, tra cứu O(1)

### Module 3: Wiki Generator *(Phase 1 — Core)*

**Yêu cầu:** Auto MD per Device, idempotent, không duplicate.

- [x] `app/wiki_generator.py` — update section với marker `<!-- DOC_SECTION:xxx -->`
- [x] `templates/model_template.md.j2` — template wiki Jinja2
- [x] `wiki/index_categories.md` + `wiki/index_groups.md` — auto-gen

### Module 4: Extractor *(Phase 2 — MVP)*

**Yêu cầu:** Fast parse PDF/Excel → text/table/JSON, cache theo sha256.

- [ ] `app/extractor_kreuzberg.py` — primary: kreuzberg, fallback: pdfplumber/python-docx
- [ ] Cache tại `~/MedicalDevices/.cache/extracted/<sha256>.json`

### Module 5: Classifier *(Phase 2 — MVP)*

**Yêu cầu:** Rule-first classify, confirm qua Telegram nếu ambiguous.

- [ ] `app/classifier.py` — DOC_TYPE_RULES theo path pattern
- [ ] Confirm flow: inline keyboard Telegram

**DOC_TYPE_RULES (theo thứ tự ưu tiên):**

| Điều kiện | doc_type |
|---|---|
| path ∋ `/tech/` | `ky_thuat` |
| path ∋ `/config/` | `cau_hinh` |
| path ∋ `/contracts/` | `hop_dong` |
| path ∋ `/price/` + filename ∋ {bao_gia, quotation, quote} | `bao_gia` |
| path ∋ `/price/` + filename ∋ {trung_thau, award} | `trung_thau` |
| path ∋ `/compare/` | `so_sanh` |
| path ∋ `/other/` | `khac` |
| ambiguous | hỏi user qua Telegram |

### Module 6: Telegram Bot + Search *(Phase 2 — MVP)*

**Yêu cầu:** Search hierarchy-aware, gửi file, confirm classify.

- [ ] `app/telegram_bot.py` — handlers: `/start`, `/find`, `/send`, inline confirm
- [ ] `app/search.py` — SQLite FTS5 + taxonomy filter + keyword

### Module 7: Advanced Features *(Phase 3 — Placeholders)*

- [ ] `app/backup.py` — file >10MB → backup + Telegram alert
- [ ] `app/compare.py` — so sánh báo giá Excel/PDF → wiki MD
- [ ] `app/reports.py` — stats theo category + export MD
- [ ] `app/voice_stt.py` — Telegram audio → Whisper STT → search
- [ ] `app/email_import.py` — batch import từ email attachments
- [ ] `app/predictive.py` — gợi ý thiết bị thay thế (heuristic)
- [ ] `app/audit.py` — multi-user audit + read-only report
- [ ] Ollama + ChromaDB semantic search
- [ ] Paperless-ngx integration (Token auth)

---

## 5. Phase Timeline

| Phase | Thời gian | Modules | Milestone |
|---|---|---|---|
| **1: Core** | Ngày 1–3 | 1, 2, 3 | Watcher + wiki auto-update, slug validate |
| **2: MVP** | Ngày 4–7 | 4, 5, 6 | UC1+UC2+UC3 pass end-to-end |
| **3: Advanced** | Ngày 8–14 | 7 | Semantic search, voice, compare |
| **4: Polish** | Ngày 15+ | — | UI mobile, stats chart, Paperless |

**Tổng:** ~2 tuần MVP usable, ~1 tháng production.  
**Chi phí:** 0đ (toàn bộ open source), chỉ thời gian dev ~40–60h.

---

## 6. Risks & Mitigation

| Risk | Mức độ | Mitigation |
|---|---|---|
| OCR kém tiếng Việt | P2 | Kreuzberg primary + Paperless fallback, train tags thủ công |
| RAM Mac M4 | P1 | Monitor Docker (cap 16GB), Ollama model ≤ 8GB |
| Classify sai | P0 | Manual approve qua Telegram + rule-first trước LLM |
| File duplicate | P1 | SHA-256 dedup trong index_store, idempotent upsert |
| Crash daemon | P0 | try/except toàn bộ + JSON log + watchdog restart |

---

## 7. Definition of Done

- ✅ **UC1:** Drop file → watcher phát hiện → bot hỏi doc_type → reply → wiki update count + link đúng section
- ✅ **UC2:** Query "Tìm cấu hình chào giá XQuang GE" → ≥1 kết quả có path → user chọn → bot gửi file
- ✅ **UC3:** "Gửi hợp đồng mới nhất x_quang_ge_optima_xr220_standard" → đúng file mới nhất trong `/contracts/`
- ✅ **Slug:** Mọi device_slug validate qua regex `^[a-z0-9]+(?:_[a-z0-9]+)*$`
- ✅ **Wiki:** Chạy `wiki_generator.py` 2 lần → không có dòng duplicate
- ✅ **Scripts:** Tất cả script trong `/scripts/` chạy được trên macOS ARM, không cần sudo

---

*Tài liệu này được duy trì song song với `implementation_plan.md` và `task.md`.*
