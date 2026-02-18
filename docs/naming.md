# Quy tắc đặt tên — MedicalDocBot

## Slug (bắt buộc)

**Regex**: `^[a-z0-9]+(?:_[a-z0-9]+)*$`

| Loại | Quy tắc | Ví dụ |
|------|---------|-------|
| Category | Từ taxonomy YAML | `chan_doan_hinh_anh` |
| Group | Từ taxonomy YAML | `x_quang` |
| Device | `<group>_<vendor>_<model>_<variant>` | `x_quang_ge_optima_xr220_standard` |

**Golden samples**:
- `x_quang_ge_optima_xr220_standard`
- `sieu_am_hitachi_arrietta_60_fulloption`

## Thư mục device

```
<category_slug>/<group_slug>/<device_slug>/
├── device.yaml
├── info/
├── tech/
├── config/
├── links/
├── price/
├── contracts/
├── compare/
└── other/
```

## File naming

Format: `<mô_tả>_<ngôn_ngữ|version>.<ext>`

| Ví dụ | Mô tả |
|-------|-------|
| `manual_vi_v2.pdf` | Manual tiếng Việt version 2 |
| `spec_en.pdf` | Spec tiếng Anh |
| `bao_gia_2026q1.xlsx` | Báo giá Q1 2026 |
| `hop_dong_2026_01.pdf` | Hợp đồng tháng 1/2026 |

## Doc types

| Slug | Ý nghĩa | Subfolder |
|------|---------|-----------|
| `ky_thuat` | Tài liệu kỹ thuật | `tech/` |
| `cau_hinh` | Cấu hình, chào giá | `config/` |
| `bao_gia` | Báo giá | `price/` |
| `trung_thau` | Trúng thầu | `price/` |
| `hop_dong` | Hợp đồng | `contracts/` |
| `so_sanh` | So sánh thiết bị | `compare/` |
| `thong_tin` | Thông tin chung | `info/` |
| `khac` | Khác | `other/` |
