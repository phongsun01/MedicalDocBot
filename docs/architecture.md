# Kiến trúc hệ thống MedicalDocBot

## Tổng quan

```
~/MedicalDevices/                    ← Whitelist path (bất biến)
├── chan_doan_hinh_anh/
│   ├── x_quang/
│   │   └── x_quang_ge_optima_xr220_standard/
│   │       ├── device.yaml          ← Metadata thiết bị
│   │       ├── tech/                ← Tài liệu kỹ thuật
│   │       ├── config/              ← Cấu hình
│   │       ├── contracts/           ← Hợp đồng
│   │       ├── price/               ← Báo giá
│   │       ├── compare/             ← So sánh
│   │       └── other/               ← Khác
│   └── sieu_am/
└── wiki/
    ├── index_categories.md          ← Auto-generated
    ├── index_groups.md              ← Auto-generated
    └── devices/
        └── model_*.md               ← Auto-generated per device
```

## Data Flow — Phase 1

```
File mới → watcher.py (debounce 3s)
         → log JSON Lines (logs/watcher.jsonl)
         → [Phase 2] classifier.py → index_store.py → wiki_generator.py
```

## Data Flow — Phase 2 (MVP)

```
File mới → watcher.py
         → extractor_kreuzberg.py (cache extracted/<sha256>.json)
         → classifier.py
             ├── openClaw skill file_classifier (confidence > 0.7)
             └── rule-based fallback (path/filename rules)
         → telegram_bot.py (confirm flow)
         → index_store.py (SQLite upsert)
         → wiki_generator.py (update model_*.md)
         → [optional] paperless_client.py (OCR + fulltext index)
```

## Components

| Component | File | Phase | Mô tả |
|-----------|------|-------|--------|
| Taxonomy | `app/taxonomy.py` | 1 | Parse 25 categories YAML |
| Slug | `app/slug.py` | 1 | Validate + normalize slug |
| Index | `app/index_store.py` | 1 | SQLite async store |
| Watcher | `app/watcher.py` | 1 | watchdog + debounce |
| Wiki | `app/wiki_generator.py` | 1 | Jinja2 → Markdown |
| Classifier | `app/classifier.py` | 2 | openClaw + rule fallback |
| Extractor | `app/extractor_kreuzberg.py` | 2 | kreuzberg Python |
| Search | `app/search.py` | 2 | Paperless + SQLite |
| Bot | `app/telegram_bot.py` | 2 | python-telegram-bot |
| openClaw | `app/openclaw_client.py` | 2 | HTTP client Node.js gateway |
| Paperless | `app/paperless_client.py` | 2 | REST client OCR/DMS |

## Constraints

- **Whitelist**: Chỉ thao tác trong `~/MedicalDevices/`
- **Idempotent**: Mọi script chạy lại → không duplicate
- **Error-safe**: try/except + JSON log, daemon không crash
- **Local-only**: Không upload dữ liệu ra ngoài
