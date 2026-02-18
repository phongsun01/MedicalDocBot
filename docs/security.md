# Security — MedicalDocBot

## Nguyên tắc bất biến

| # | Quy tắc | Lý do |
|---|---------|-------|
| 1 | **100% local** — không upload dữ liệu ra ngoài | Bảo mật dữ liệu y tế |
| 2 | **Whitelist path**: chỉ `~/MedicalDevices/` | Tránh thao tác ngoài ý muốn |
| 3 | **Cấm**: `rm -rf`, `sudo`, xóa hàng loạt | An toàn dữ liệu |
| 4 | **Idempotent**: chạy lại không tạo duplicate | Tính ổn định |
| 5 | **Error-safe**: try/except + JSON log | Daemon không crash |

## Whitelist enforcement

`watcher.py` kiểm tra mọi path trước khi xử lý:
```python
try:
    Path(path).relative_to(self._root)
except ValueError:
    logger.warning("Path ngoài whitelist, bỏ qua: %s", path)
    return True  # ignore
```

## Telegram bot security

- `dmPolicy: "pairing"` — chỉ user đã approve mới dùng được bot
- Admin chat ID whitelist trong `.env`
- Không expose file path tuyệt đối trong reply

## Secrets management

- Tất cả secrets trong `.env` (gitignored)
- `.env.example` chỉ chứa placeholder
- Không hardcode token trong code
