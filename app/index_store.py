"""
index_store.py — SQLite store cho MedicalDocBot
Ghi nhận file, doc_type, sha256, timestamps. Idempotent (upsert theo sha256).
Mọi lỗi được log JSON, không crash daemon.
"""

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from app.config import DB_PATH, assert_within_base_dir

logger = logging.getLogger("medicalbot.index_store")

# ── Schema SQL ────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256       TEXT    UNIQUE NOT NULL,
    path         TEXT    NOT NULL,
    device_slug  TEXT,
    doc_type     TEXT,
    category_slug TEXT,
    group_slug   TEXT,
    size_bytes   INTEGER,
    created_at   TEXT,
    updated_at   TEXT,
    indexed_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_device_slug  ON files(device_slug);
CREATE INDEX IF NOT EXISTS idx_files_doc_type     ON files(doc_type);
CREATE INDEX IF NOT EXISTS idx_files_category     ON files(category_slug);

CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type   TEXT    NOT NULL,   -- created | modified | deleted | classified
    path         TEXT    NOT NULL,
    sha256       TEXT,
    metadata     TEXT,               -- JSON blob cho thông tin thêm
    timestamp    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_path      ON events(path);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

CREATE TABLE IF NOT EXISTS pending_classification (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256       TEXT    UNIQUE NOT NULL,
    path         TEXT    NOT NULL,
    device_slug  TEXT,
    created_at   TEXT    NOT NULL,
    telegram_msg_id INTEGER         -- message_id Telegram đang chờ confirm
);
"""


@contextmanager
def _get_conn(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager trả connection SQLite với WAL mode."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now_iso() -> str:
    """Trả timestamp ISO 8601 UTC hiện tại."""
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: Path = DB_PATH) -> None:
    """Khởi tạo schema SQLite. Idempotent — chạy lại không tạo duplicate."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _get_conn(db_path) as conn:
        conn.executescript(_DDL)
    logger.info("SQLite DB khởi tạo tại: %s", db_path)


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """
    Tính SHA-256 của file theo từng chunk (tránh OOM với file lớn).
    
    Args:
        file_path: Đường dẫn file
        chunk_size: Kích thước chunk đọc (bytes)
        
    Returns:
        Chuỗi hex SHA-256
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def upsert_file(
    file_path: Path,
    device_slug: Optional[str] = None,
    doc_type: Optional[str] = None,
    category_slug: Optional[str] = None,
    group_slug: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> str:
    """
    Upsert thông tin file vào bảng files.
    Nếu sha256 đã tồn tại → update path + metadata.
    
    Args:
        file_path: Đường dẫn tuyệt đối của file
        device_slug: Slug thiết bị (nếu đã biết)
        doc_type: Loại tài liệu (nếu đã phân loại)
        category_slug: Slug danh mục
        group_slug: Slug nhóm thiết bị
        db_path: Đường dẫn SQLite DB
        
    Returns:
        sha256 của file
        
    Raises:
        ValueError: Nếu file nằm ngoài whitelist
    """
    try:
        assert_within_base_dir(file_path)
        sha256 = compute_sha256(file_path)
        stat = file_path.stat()
        now = _now_iso()

        with _get_conn(db_path) as conn:
            conn.execute(
                """
                INSERT INTO files
                    (sha256, path, device_slug, doc_type, category_slug, group_slug,
                     size_bytes, created_at, updated_at, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sha256) DO UPDATE SET
                    path          = excluded.path,
                    device_slug   = COALESCE(excluded.device_slug, files.device_slug),
                    doc_type      = COALESCE(excluded.doc_type, files.doc_type),
                    category_slug = COALESCE(excluded.category_slug, files.category_slug),
                    group_slug    = COALESCE(excluded.group_slug, files.group_slug),
                    size_bytes    = excluded.size_bytes,
                    updated_at    = excluded.updated_at,
                    indexed_at    = excluded.indexed_at
                """,
                (
                    sha256,
                    str(file_path),
                    device_slug,
                    doc_type,
                    category_slug,
                    group_slug,
                    stat.st_size,
                    datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                    datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    now,
                ),
            )

        logger.debug("Upsert file: %s (sha256=%s)", file_path.name, sha256[:8])
        return sha256

    except Exception as exc:
        _log_error("upsert_file", str(file_path), exc)
        raise


def update_doc_type(sha256: str, doc_type: str, db_path: Path = DB_PATH) -> None:
    """Cập nhật doc_type cho file đã index (sau khi user confirm qua Telegram)."""
    try:
        with _get_conn(db_path) as conn:
            conn.execute(
                "UPDATE files SET doc_type = ?, updated_at = ? WHERE sha256 = ?",
                (doc_type, _now_iso(), sha256),
            )
        logger.info("Cập nhật doc_type='%s' cho sha256=%s", doc_type, sha256[:8])
    except Exception as exc:
        _log_error("update_doc_type", sha256, exc)
        raise


def log_event(
    event_type: str,
    path: str,
    sha256: Optional[str] = None,
    metadata: Optional[dict] = None,
    db_path: Path = DB_PATH,
) -> None:
    """
    Ghi event vào bảng events (watcher, classification, v.v.)
    Không raise exception — chỉ log lỗi.
    """
    try:
        with _get_conn(db_path) as conn:
            conn.execute(
                "INSERT INTO events (event_type, path, sha256, metadata, timestamp) VALUES (?,?,?,?,?)",
                (
                    event_type,
                    path,
                    sha256,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                    _now_iso(),
                ),
            )
    except Exception as exc:
        _log_error("log_event", path, exc)


def get_file_by_sha256(sha256: str, db_path: Path = DB_PATH) -> Optional[dict]:
    """Tra cứu file theo sha256. Trả None nếu không tìm thấy."""
    try:
        with _get_conn(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE sha256 = ?", (sha256,)
            ).fetchone()
        return dict(row) if row else None
    except Exception as exc:
        _log_error("get_file_by_sha256", sha256, exc)
        return None


def get_files_by_device(
    device_slug: str,
    doc_type: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> list[dict]:
    """
    Lấy danh sách file của một thiết bị.
    Có thể filter thêm theo doc_type.
    """
    try:
        with _get_conn(db_path) as conn:
            if doc_type:
                rows = conn.execute(
                    "SELECT * FROM files WHERE device_slug = ? AND doc_type = ? ORDER BY updated_at DESC",
                    (device_slug, doc_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM files WHERE device_slug = ? ORDER BY updated_at DESC",
                    (device_slug,),
                ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        _log_error("get_files_by_device", device_slug, exc)
        return []


def add_pending_classification(
    sha256: str,
    path: str,
    device_slug: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Thêm file vào hàng đợi chờ phân loại doc_type qua Telegram."""
    try:
        with _get_conn(db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO pending_classification
                    (sha256, path, device_slug, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (sha256, path, device_slug, _now_iso()),
            )
    except Exception as exc:
        _log_error("add_pending_classification", path, exc)


def remove_pending_classification(sha256: str, db_path: Path = DB_PATH) -> None:
    """Xóa file khỏi hàng đợi sau khi đã phân loại xong."""
    try:
        with _get_conn(db_path) as conn:
            conn.execute(
                "DELETE FROM pending_classification WHERE sha256 = ?", (sha256,)
            )
    except Exception as exc:
        _log_error("remove_pending_classification", sha256, exc)


def _log_error(operation: str, context: str, exc: Exception) -> None:
    """Ghi lỗi dạng JSON log (không crash)."""
    logger.error(
        json.dumps(
            {
                "operation": operation,
                "context": context,
                "error": str(exc),
                "type": type(exc).__name__,
            },
            ensure_ascii=False,
        )
    )


# ── CLI test nhanh ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import tempfile

    logging.basicConfig(level=logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmp:
        test_db = Path(tmp) / "test.db"
        init_db(test_db)
        print("✓ init_db OK")

        # Tạo file test
        test_file = Path(tmp) / "test.pdf"
        test_file.write_bytes(b"PDF content test")

        # Patch whitelist để test
        import app.config as cfg
        original_base = cfg.BASE_DIR
        cfg.BASE_DIR = Path(tmp)

        sha = upsert_file(test_file, device_slug="test_device", db_path=test_db)
        print(f"✓ upsert_file: sha256={sha[:8]}...")

        row = get_file_by_sha256(sha, test_db)
        assert row is not None
        assert row["device_slug"] == "test_device"
        print("✓ get_file_by_sha256 OK")

        update_doc_type(sha, "ky_thuat", test_db)
        row2 = get_file_by_sha256(sha, test_db)
        assert row2["doc_type"] == "ky_thuat"
        print("✓ update_doc_type OK")

        log_event("created", str(test_file), sha, {"test": True}, test_db)
        print("✓ log_event OK")

        cfg.BASE_DIR = original_base

    print("\n✓ index_store.py OK")
    sys.exit(0)
