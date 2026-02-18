"""
config.py — Cấu hình trung tâm cho MedicalDocBot
Tải biến môi trường từ .env, expose các hằng số dùng toàn hệ thống.
Singleton pattern: import config ở bất kỳ đâu đều nhận cùng giá trị.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Tải .env từ thư mục gốc project (2 cấp trên app/)
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Đường dẫn dữ liệu ─────────────────────────────────────────────────────────
# Thư mục gốc lưu tài liệu — WHITELIST PATH, chỉ thao tác trong này
BASE_DIR: Path = Path(
    os.getenv("MEDICAL_DEVICES_DIR", str(Path.home() / "MedicalDevices"))
).expanduser().resolve()

# Thư mục database SQLite
DB_PATH: Path = Path(
    os.getenv("DB_PATH", str(BASE_DIR / ".db" / "medicalbot.db"))
).expanduser().resolve()

# Thư mục cache kết quả extract
EXTRACT_CACHE_DIR: Path = Path(
    os.getenv("EXTRACT_CACHE_DIR", str(BASE_DIR / ".cache" / "extracted"))
).expanduser().resolve()

# Thư mục wiki (index + model pages)
WIKI_DIR: Path = BASE_DIR / "wiki"

# Thư mục taxonomy YAML
TAXONOMY_PATH: Path = _PROJECT_ROOT / "data" / "taxonomy.yaml"

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Danh sách user ID được phép dùng bot (whitelist)
_allowed_raw = os.getenv("TELEGRAM_ALLOWED_USERS", "")
ALLOWED_USERS: list[int] = [
    int(uid.strip())
    for uid in _allowed_raw.split(",")
    if uid.strip().isdigit()
]

# ── Watcher ───────────────────────────────────────────────────────────────────
WATCHER_DEBOUNCE_SECONDS: float = float(
    os.getenv("WATCHER_DEBOUNCE_SECONDS", "3")
)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR: Path = _PROJECT_ROOT / "logs"

# ── Regex slug ────────────────────────────────────────────────────────────────
SLUG_PATTERN: str = r"^[a-z0-9]+(?:_[a-z0-9]+)*$"

# ── Kiểm tra whitelist path ───────────────────────────────────────────────────
def assert_within_base_dir(path: Path) -> None:
    """
    Đảm bảo path nằm trong BASE_DIR.
    Ném ValueError nếu vi phạm whitelist.
    """
    try:
        path.resolve().relative_to(BASE_DIR)
    except ValueError:
        raise ValueError(
            f"Truy cập bị từ chối: '{path}' nằm ngoài whitelist '{BASE_DIR}'"
        )


def setup_logging() -> logging.Logger:
    """Khởi tạo logger chuẩn cho toàn hệ thống."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    return logging.getLogger("medicalbot")


# Khởi tạo thư mục cần thiết khi import
BASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
EXTRACT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
WIKI_DIR.mkdir(parents=True, exist_ok=True)
