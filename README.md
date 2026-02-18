# MedicalDocBot

> Hệ thống quản lý kho tài liệu thiết bị y tế — 100% local, Mac Mini M4 24GB.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Tổng quan

MedicalDocBot là hệ thống DMS (Document Management System) hybrid chạy hoàn toàn local:
- **Current Phase**: Phase 2.1 — Setup & Admin (In Progress)
- **Status**: ✅ Phase 1 Completed | 🔄 Phase 2 Started
- **Next Milestone**: v2.0-mvp (Telegram Integration & AI Classification)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Database | SQLite (aiosqlite) |
| File watch | watchdog 4.x |
| Template | Jinja2 3.x |
| Bot | python-telegram-bot 21.x |
| Extractor | kreuzberg (Rust core, ARM64) |
| AI Gateway | openClaw (Node.js) |
| OCR/DMS | Paperless-ngx (Phase 2) |

## Cấu trúc thư mục

```
MedicalDocBot/
├── app/                    # Core Python modules
│   ├── taxonomy.py         # Parse taxonomy 25 categories
│   ├── slug.py             # Validate + normalize slug
│   ├── index_store.py      # SQLite index
│   ├── watcher.py          # File watcher + event queue
│   ├── wiki_generator.py   # Jinja2 → Markdown wiki
│   ├── classifier.py       # Doc type classifier (Phase 2)
│   ├── search.py           # Search engine (Phase 2)
│   └── telegram_bot.py     # Telegram bot (Phase 2)
├── data/
│   └── taxonomy.yaml       # 25 categories thiết bị y tế
├── docs/                   # Tài liệu dự án
│   ├── PRD.md
│   ├── USECASES.md
│   ├── SPECS.md
│   └── ROADMAP.md
├── scripts/                # Shell scripts
│   ├── setup_taxonomy_folders.sh
│   ├── create_device.sh
│   ├── seed_samples.sh
│   └── run_dev.sh
├── templates/              # Jinja2 templates
│   ├── model_template.md.j2
│   └── device_yaml_template.yaml.j2
├── logs/                   # JSON logs (gitignored)
├── config.yaml             # Cấu hình tập trung
├── requirements.txt
└── pyproject.toml
```

## 🚀 Quick Setup (Phase 2)

### Prerequisites
- Node.js 22+
- Python 3.11+
- Anthropic API Key
- Telegram Bot Token

### Installation
1. **Install openClaw**:
   ```bash
   npm install -g openclaw@latest
   openclaw doctor
   ```
2. **Onboard & Config**:
   ```bash
   export ANTHROPIC_API_KEY="sk-..."
   openclaw onboard --non-interactive ...
   ```
3. **Setup Python Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## 📂 Project Structure

## Cấu hình

Sao chép `.env.example` thành `.env` và điền thông tin:

```bash
cp .env.example .env
```

Chỉnh sửa `config.yaml` để thay đổi paths và settings.

## Hierarchy tài liệu

```
~/MedicalDevices/
├── chan_doan_hinh_anh/
│   ├── x_quang/
│   │   └── x_quang_ge_optima_xr220_standard/
│   │       ├── device.yaml
│   │       ├── tech/
│   │       ├── config/
│   │       ├── contracts/
│   │       └── ...
│   └── sieu_am/
└── xet_nghiem_huyet_hoc/
    └── ...
```

## Phase 1 — Core (hiện tại)

- [x] Taxonomy 25 categories
- [x] Slug validation + normalization
- [x] SQLite index store
- [x] File watcher + debounce
- [x] Wiki generator (Jinja2)
- [x] Setup scripts

## Phase 2 — MVP (tiếp theo)

- [ ] openClaw integration (classifier)
- [ ] Paperless-ngx (OCR + search)
- [ ] Telegram bot (/find, /send, /stats)

## Constraints

- ✅ 100% local — không upload dữ liệu ra ngoài
- ✅ Whitelist path: chỉ `~/MedicalDevices/`
- ✅ Không `sudo`, không `rm -rf`
- ✅ Idempotent: chạy lại không tạo duplicate
- ✅ Slug regex: `^[a-z0-9]+(?:_[a-z0-9]+)*$`

## License

MIT
