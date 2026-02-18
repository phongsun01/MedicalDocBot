# PRD: MedicalDocBot — Hệ thống Wiki + Bot quản lý tài liệu thiết bị y tế

**Version**: 1.2 | **Date**: 18/02/2026 | **Owner**: Phong | **Target**: Mac Mini M4 24GB, self-hosted 24/7

---

## 1. Tổng quan & Mục tiêu

**Vấn đề**: Tìm spec/contract/giá thiết bị y tế (PDF/DOC/Excel, VI/EN/scan) qua Explorer/folder thủ công mất thời gian và dễ nhầm.

**Giải pháp**: Hệ thống DMS hybrid chạy 100% local:
- **Kreuzberg** (Python) — extract text/metadata từ 75+ định dạng
- **Paperless-ngx** (Docker) — OCR + fulltext index PDF scan
- **openClaw** (Node.js) — AI assistant gateway + Telegram bot 24/7
- **SQLite** — index nhanh, không cần server
- **Obsidian wiki** — xem tài liệu dạng MD graph (optional)

**KPI mục tiêu**:
- Tìm tài liệu < 5 giây, độ chính xác classify > 90%
- Scale 1.000+ thiết bị, 10.000+ files
- 100% local — không upload dữ liệu y tế ra ngoài

**Hierarchy thiết bị**:
```
Loại (Category) → Nhóm (Group) → Thiết bị (Device)
├── chan_doan_hinh_anh/
│   ├── sieu_am/  → sieu_am_hitachi_arrietta_60_fulloption/
│   └── x_quang/  → x_quang_ge_optima_xr220_standard/
└── kiem_soat_nhiem_khuan/
    └── noi_hap/ → autoclave_getinge_gs_series/
```

---

## 2. User Stories & Requirements

### 2.1 Core Use Cases

| ID | Actor | Story | Priority | Phase |
|----|-------|-------|----------|-------|
| UC1 | User | Thêm file PDF/Excel vào folder device → watcher phát hiện → openClaw classify → Telegram confirm → wiki MD update tự động | P0 | 1 |
| UC2 | User (mobile) | Telegram: `/find cấu hình chào giá XQuang GE` → Paperless + SQLite search → top results → gửi file | P0 | 2 |
| UC3 | User | `/send hop_dong mới nhất x_quang_ge_optima_xr220_standard` → bot gửi đúng file mới nhất trong `/contracts/` | P0 | 2 |
| UC4 | User | So sánh báo giá GE vs Shimadzu từ Excel/PDF → sinh wiki MD compare | P1 | 3 |
| UC5 | Admin | Stats: số contract > 10MB loại Chẩn đoán hình ảnh → bảng + MD report | P1 | 3 |
| UC6 | System | File mới > 10MB → backup tự động + Telegram alert | P1 | 3 |
| UC7 | User | Gửi voice Telegram → STT (openClaw) → search → trả kết quả | P2 | 3 |
| UC8 | Admin | Batch import email attachments → classify → watcher pipeline | P2 | 3 |
| UC9 | System | Gợi ý thiết bị thay thế dựa trên compare + index | P2 | 3 |
| UC10 | Admin | Audit log multi-user + export read-only report | P2 | 3 |

### 2.2 Non-Functional Requirements

| Yêu cầu | Chỉ tiêu |
|---------|---------|
| Performance | Extract batch 100 files < 2 phút; search < 3 giây |
| Storage | Files raw + DB index < 10GB ban đầu |
| Uptime | 24/7, Docker healthcheck, watcher auto-restart |
| Security | Local-only; whitelist `~/MedicalDevices`; approve thủ công lệnh nhạy |
| Idempotent | Mọi script chạy lại không tạo duplicate |
| Error handling | try/except + JSON log; daemon không crash khi lỗi đơn lẻ |

---

## 3. Kiến trúc hệ thống

```
┌─────────────────────┐   inotify/watchdog   ┌──────────────────────┐
│  ~/MedicalDevices/  │ ──────────────────▶  │  watcher.py          │
│  cat/group/device/  │                       │  (debounce 3s)       │
└─────────────────────┘                       └──────────┬───────────┘
                                                         │ event queue
                              ┌──────────────────────────┼──────────────────────────┐
                              ▼                          ▼                          ▼
                   ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
                   │  classifier.py   │      │  index_store.py  │      │  wiki_generator  │
                   │  openClaw skill  │      │  SQLite + sha256 │      │  Jinja2 → MD     │
                   │  → rule fallback │      └──────────────────┘      └──────────────────┘
                   └────────┬─────────┘
                            │ doc_type confirmed
                   ┌────────▼─────────┐
                   │  telegram_bot.py │  ◀── /find /send /stats
                   │  python-telegram │
                   │  -bot            │
                   └────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ Kreuzberg    │  │ Paperless-ngx│  │ openClaw     │
   │ Python lib   │  │ Docker :8000 │  │ Node.js :18789│
   │ (fallback    │  │ OCR + index  │  │ Skills + STT │
   │  extractor)  │  │ (Phase 2)    │  │ (Phase 2)    │
   └──────────────┘  └──────────────┘  └──────────────┘
```

**Data flow chính**:
```
File mới → watcher.py → sha256 check → kreuzberg extract metadata
         → classifier.py (openClaw skill / rule-based fallback)
         → Telegram confirm → index_store.py upsert
         → wiki_generator.py update model_*.md
         → Paperless upload (nếu enabled, Phase 2)
```

---

## 4. Modules & Tasks

### Phase 1 — Core (Ngày 1–3)

**Mục tiêu**: Hạ tầng ổn định, chạy độc lập, không cần LLM/OCR/openClaw.

| Module | File | Mô tả |
|--------|------|--------|
| Taxonomy | `app/taxonomy.py` | Parse YAML 25 categories, lookup category/group |
| Slug | `app/slug.py` | Validate + normalize, regex `^[a-z0-9]+(?:_[a-z0-9]+)*$` |
| Index | `app/index_store.py` | SQLite async (aiosqlite), upsert idempotent |
| Watcher | `app/watcher.py` | watchdog + debounce 3s + JSON log |
| Wiki | `app/wiki_generator.py` | Jinja2 render, update section, no duplicate |
| Templates | `templates/*.j2` | model_template.md.j2, device_yaml_template.yaml.j2 |
| Scripts | `scripts/` | setup_taxonomy_folders.sh, create_device.sh/py, seed_samples.sh |
| Config | `config.yaml` | Paths, feature flags, service URLs |
| Docs | `docs/` | architecture.md, naming.md, security.md |

**Phase Gate 1**:
- [ ] `seed_samples.sh` chạy OK, không duplicate
- [ ] Drop 1 file → watcher log đúng event
- [ ] Wiki MD update đúng count + section
- [ ] Slug golden samples pass: `x_quang_ge_optima_xr220_standard`, `sieu_am_hitachi_arrietta_60_fulloption`

### Phase 2 — MVP (Ngày 4–7)

**Mục tiêu**: Giải UC1, UC2, UC3 + tích hợp openClaw + Paperless.

| Module | File | Mô tả |
|--------|------|--------|
| openClaw client | `app/openclaw_client.py` | HTTP client → openClaw Gateway :18789 |
| Paperless client | `app/paperless_client.py` | REST client Paperless-ngx :8000 |
| Extractor | `app/extractor_kreuzberg.py` | Extract text/metadata, cache `extracted/<sha256>.json` |
| Classifier | `app/classifier.py` | openClaw skill → rule-based fallback → Telegram confirm |
| Search | `app/search.py` | Paperless fulltext + SQLite + taxonomy-aware merge |
| Bot | `app/telegram_bot.py` | /start /find /send /stats + inline keyboard |
| Docker | `docker-compose.yml` | openclaw + paperless + bot + watcher |
| Env | `.env.example` | Template biến môi trường |
| Tests | `scripts/test_uc1-3.sh` | End-to-end test UC1, UC2, UC3 |

**Phase Gate 2**:
- [ ] openClaw `/health` → 200 OK
- [ ] Paperless `/api/documents/` → auth OK, trả list
- [ ] UC1 + UC2 + UC3 pass end-to-end

### Phase 3 — Advanced (Ngày 8–14)

| Module | File | UC |
|--------|------|----|
| Backup | `app/backup.py` | UC6 |
| Compare | `app/compare.py` | UC4 |
| Reports | `app/reports.py` | UC5 |
| Voice STT | `app/voice_stt.py` | UC7 |
| Email import | `app/email_import.py` | UC8 |
| Predictive | `app/predictive.py` | UC9 |
| Audit | `app/audit.py` | UC10 |

---

## 5. Timeline & Dependencies

| Phase | Thời gian | Milestone | Điều kiện |
|-------|-----------|-----------|-----------|
| **1: Core** | Ngày 1–3 | Watcher + wiki auto-update | — |
| **2: MVP** | Ngày 4–7 | Bot search + gửi file | Phase Gate 1 ✓ |
| **3: Advanced** | Ngày 8–14 | Voice, compare, audit | Phase Gate 2 ✓ |
| **4: Polish** | Ngày 15+ | UI mobile, stats chart | All |

**Tổng**: ~2 tuần MVP usable, ~1 tháng production.
**Chi phí**: 0đ (100% open source).

---

## 6. Tech Stack

| Layer | Technology | Ghi chú |
|-------|-----------|---------|
| Language | Python 3.11+ | snake_case, comment tiếng Việt |
| DB | SQLite + aiosqlite | Không cần server |
| File watch | watchdog 4.x | Cross-platform |
| Template | Jinja2 3.x | MD + YAML generation |
| Bot | python-telegram-bot 21.x | Async |
| Extractor | kreuzberg (Python) | ARM64 macOS, 75+ formats |
| OCR/DMS | Paperless-ngx (Docker) | Port 8000, Phase 2 |
| AI Gateway | openClaw (Node.js) | Port 18789, Skills registry |
| Env | `.venv` (Python) | `python -m venv .venv` |

---

## 7. Risks & Mitigation

| Risk | Mức độ | Mitigation |
|------|--------|-----------|
| OCR kém tiếng Việt | P1 | Train Paperless + fallback Kreuzberg |
| RAM M4 quá tải | P1 | Cap Docker 16GB, monitor `docker stats` |
| Classify sai | P0 | Manual approve qua Telegram trước khi commit |
| openClaw offline | P0 | Rule-based classifier fallback tự động |
| Paperless offline | P0 | Kreuzberg extractor fallback tự động |

---

## 8. Constraints (bất biến)

- ✅ 100% local — tuyệt đối không upload dữ liệu ra ngoài
- ✅ Whitelist path: chỉ thao tác trong `~/MedicalDevices/`
- ✅ Cấm: `rm -rf`, `sudo`, bất kỳ lệnh xóa hàng loạt
- ✅ Idempotent: mọi script chạy lại không tạo duplicate
- ✅ Error không crash daemon (try/except + JSON log)
- ✅ Slug regex: `^[a-z0-9]+(?:_[a-z0-9]+)*$`

**Phân loại (Taxonomy V2)**:
- **Level 1 (Category)**: `chan_doan_hinh_anh`, `xet_nghiem_huyet_hoc`, `gay_me_may_tho`...
- **Level 2 (Group)**: `x_quang`, `ct_scanner`, `may_dem_tb_mau`, `may_gay_me`...
