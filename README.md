# MedicalDocBot

Hệ thống quản lý kho tài liệu thiết bị y tế — **100% local** trên Mac mini M4 24GB.  
Tích hợp Telegram Bot 24/7 để tìm kiếm, tra cứu và gửi tài liệu.

> ⚠️ **Bảo mật**: Mọi dữ liệu lưu tại `~/MedicalDevices/`. Tuyệt đối không upload cloud.

## Cài đặt nhanh

```bash
# 1. Clone repo
cd MedicalDocBot

# 2. Tạo virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Cấu hình môi trường
cp .env.example .env
# Điền TELEGRAM_BOT_TOKEN và TELEGRAM_ALLOWED_USERS vào .env

# 5. Setup thư mục taxonomy
bash scripts/setup_taxonomy_folders.sh

# 6. Tạo dữ liệu mẫu (optional)
bash scripts/seed_samples.sh

# 7. Chạy (watcher + bot)
bash scripts/run_dev.sh
```

## Cấu trúc dữ liệu

```
~/MedicalDevices/
├── 01_chan_doan_hinh_anh/
│   ├── x_quang/
│   │   └── x_quang_ge_optima_xr220_standard/
│   │       ├── device.yaml
│   │       ├── tech/        ← Tài liệu kỹ thuật
│   │       ├── contracts/   ← Hợp đồng
│   │       ├── price/       ← Báo giá / trúng thầu
│   │       ├── config/      ← Cấu hình
│   │       ├── compare/     ← So sánh
│   │       └── other/       ← Khác
│   └── ...
├── wiki/
│   ├── index_categories.md
│   ├── index_groups.md
│   └── model_*.md
└── .db/medicalbot.db
```

## Tạo thiết bị mới

```bash
bash scripts/create_device.sh \
  --category chan_doan_hinh_anh \
  --group x_quang \
  --vendor "GE Healthcare" \
  --model "Optima XR220" \
  --year 2018 \
  --risk-class C \
  --hs-code "9022.12.00"
```

## Lệnh Telegram Bot

| Lệnh | Mô tả |
|---|---|
| `/start` | Giới thiệu và hướng dẫn |
| `/find <query>` | Tìm kiếm tài liệu |
| `/send <slug> <doc_type>` | Gửi file mới nhất |

## Taxonomy

25 nhóm thiết bị y tế theo **TT 30/2015/TT-BYT** + **NĐ 98/2021/NĐ-CP**.  
Xem chi tiết: `data/taxonomy.yaml`

## Architecture

- **Phase 1 (Core)**: Watcher + Index + Wiki Generator
- **Phase 2 (MVP)**: Extractor + Classifier + Telegram Bot + Search
- **Phase 3 (Advanced)**: Backup, Compare, Reports, Voice STT, Email Import

Xem thêm: `docs/architecture.md`
