"""
index_store.py — SQLite index cho tài liệu thiết bị y tế.

Lưu trữ metadata file: path, sha256, doc_type, device_slug,
category_slug, timestamps. Hỗ trợ async với aiosqlite.
Idempotent: upsert theo path (không tạo duplicate).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

# Schema SQLite
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT    NOT NULL UNIQUE,
    sha256       TEXT    NOT NULL,
    doc_type     TEXT    NOT NULL DEFAULT 'khac',
    device_slug  TEXT,
    category_slug TEXT,
    group_slug   TEXT,
    vendor       TEXT,
    model        TEXT,
    summary      TEXT,
    size_bytes   INTEGER NOT NULL DEFAULT 0,
    confirmed    INTEGER NOT NULL DEFAULT 0,  -- 0: chờ confirm, 1: đã confirm
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    indexed_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_doc_type      ON files(doc_type);
CREATE INDEX IF NOT EXISTS idx_device_slug   ON files(device_slug);
CREATE INDEX IF NOT EXISTS idx_category_slug ON files(category_slug);
CREATE INDEX IF NOT EXISTS idx_sha256        ON files(sha256);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT    NOT NULL,  -- created, modified, deleted
    file_path  TEXT    NOT NULL,
    ts         TEXT    NOT NULL,
    processed  INTEGER NOT NULL DEFAULT 0
);
"""


def _now_iso() -> str:
    """Trả về timestamp ISO 8601 UTC hiện tại."""
    return datetime.now(UTC).isoformat()


# compute_sha256 moved to app.utils


class IndexStore:
    """
    SQLite index store cho tài liệu thiết bị y tế.

    Ví dụ sử dụng:
        store = IndexStore("data/medicalbot.db")
        await store.init()
        await store.upsert_file(path="/path/to/file.pdf", sha256="abc...", doc_type="ky_thuat")
        files = await store.search(doc_type="ky_thuat", device_slug="x_quang_ge_optima_xr220_standard")
    """

    def __init__(self, db_path: str | Path) -> None:
        """
        Khởi tạo IndexStore.

        Args:
            db_path: Đường dẫn file SQLite
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None

    def is_connected(self) -> bool:
        """Kiểm tra kết nối CSDL."""
        return self._conn is not None

    async def init(self) -> None:
        """Tạo schema nếu chưa có và migrate nếu cần."""
        if not self._conn:
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row

        await self._conn.executescript(_SCHEMA_SQL)

        # Migration: Kiểm tra và thêm cột mới nếu thiếu (cho DB cũ)
        async with self._conn.execute("PRAGMA table_info(files)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if "vendor" not in columns:
            logger.info("⚡️ Migrating DB: Adding column 'vendor'")
            await self._conn.execute("ALTER TABLE files ADD COLUMN vendor TEXT")
        if "model" not in columns:
            logger.info("⚡️ Migrating DB: Adding column 'model'")
            await self._conn.execute("ALTER TABLE files ADD COLUMN model TEXT")
        if "summary" not in columns:
            logger.info("⚡️ Migrating DB: Adding column 'summary'")
            await self._conn.execute("ALTER TABLE files ADD COLUMN summary TEXT")
        if "search_text" not in columns:
            logger.info("⚡️ Migrating DB: Adding column 'search_text'")
            await self._conn.execute("ALTER TABLE files ADD COLUMN search_text TEXT")

        # Tạo index cho cột mới sau khi chắc chắn cột đã tồn tại
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_vendor ON files(vendor)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON files(model)")

        # Cập nhật dữ liệu search_text cho các file cũ
        import unidecode

        async def _backfill():
            try:
                async with self._conn.execute(
                    "SELECT id, path, vendor, model, summary FROM files WHERE search_text IS NULL"
                ) as cursor:
                    old_rows = await cursor.fetchall()

                if old_rows:
                    logger.info("⚡️ Migrating DB: Backfilling search_text for %d files in background...", len(old_rows))
                    updates = []
                    for row in old_rows:
                        search_data = f"{row[1]} {row[2] or ''} {row[3] or ''} {row[4] or ''}".lower()
                        search_text = unidecode.unidecode(search_data)
                        updates.append((search_text, row[0]))

                    await self._conn.executemany(
                        "UPDATE files SET search_text = ? WHERE id = ?", updates
                    )
                    await self._conn.commit()
                    logger.info("✅ Migration: search_text backfill complete.")
            except Exception as e:
                logger.error("Lỗi khi backfill search_text: %s", e)

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_backfill())
        except RuntimeError:
            logger.warning("Không có running event loop, bỏ qua backfill search_text.")

        await self._conn.commit()
        logger.info("IndexStore khởi tạo: %s", self._db_path)

    async def close(self) -> None:
        """Đóng kết nối database."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def upsert_file(
        self,
        path: str | Path,
        sha256: str,
        doc_type: str = "khac",
        device_slug: str | None = None,
        category_slug: str | None = None,
        group_slug: str | None = None,
        vendor: str | None = None,
        model: str | None = None,
        summary: str | None = None,
        size_bytes: int | None = None,
        confirmed: bool = False,
    ) -> int:
        """
        Thêm hoặc cập nhật record file (idempotent theo path).

        Args:
            path: Đường dẫn tuyệt đối của file
            sha256: Hash SHA256 của file
            doc_type: Loại tài liệu (ky_thuat, hop_dong, ...)
            device_slug: Slug thiết bị
            category_slug: Slug category
            group_slug: Slug group
            size_bytes: Kích thước file (bytes)
            confirmed: Đã được user confirm chưa

        Returns:
            ID của record (mới hoặc cập nhật)
        """
        path_str = str(path)
        now = _now_iso()

        # Tự động lấy size nếu không truyền
        if size_bytes is None:
            try:
                size_bytes = os.path.getsize(path_str)
            except OSError:
                size_bytes = 0

        if not self._conn:
            await self.init()

        # Kiểm tra đã tồn tại chưa
        async with self._conn.execute(
            "SELECT id, created_at FROM files WHERE path = ?", (path_str,)
        ) as cursor:
            existing = await cursor.fetchone()

        import unidecode

        search_data = f"{path_str} {vendor or ''} {model or ''} {summary or ''} {doc_type}".lower()
        search_text = unidecode.unidecode(search_data)

        if existing:
            # Cập nhật record hiện có
            await self._conn.execute(
                """
                UPDATE files SET
                    sha256 = ?, doc_type = ?, device_slug = ?,
                    category_slug = ?, group_slug = ?,
                    vendor = ?, model = ?, summary = ?,
                    size_bytes = ?, confirmed = ?, updated_at = ?, indexed_at = ?,
                    search_text = ?
                WHERE path = ?
                """,
                (
                    sha256,
                    doc_type,
                    device_slug,
                    category_slug,
                    group_slug,
                    vendor,
                    model,
                    summary,
                    size_bytes,
                    int(confirmed),
                    now,
                    now,
                    search_text,
                    path_str,
                ),
            )
            record_id = existing[0]
            logger.debug("Cập nhật file: %s (id=%d)", path_str, record_id)
        else:
            # Thêm record mới
            cursor = await self._conn.execute(
                """
                INSERT INTO files
                    (path, sha256, doc_type, device_slug, category_slug, group_slug,
                        vendor, model, summary,
                        size_bytes, confirmed, created_at, updated_at, indexed_at, search_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    path_str,
                    sha256,
                    doc_type,
                    device_slug,
                    category_slug,
                    group_slug,
                    vendor,
                    model,
                    summary,
                    size_bytes,
                    int(confirmed),
                    now,
                    now,
                    now,
                    search_text,
                ),
            )
            record_id = cursor.lastrowid
            logger.debug("Thêm file mới: %s (id=%d)", path_str, record_id)

        await self._conn.commit()

        return record_id

    async def delete_file(self, path: str | Path) -> None:
        """
        Xóa file khỏi index.

        Args:
            path: Đường dẫn file cần xóa
        """
        if not self._conn:
            await self.init()
        await self._conn.execute("DELETE FROM files WHERE path = ?", (str(path),))
        await self._conn.commit()
        logger.info("Đã xóa file khỏi DB: %s", path)

    async def get_file(self, path: str | Path) -> dict[str, Any] | None:
        """
        Lấy thông tin file theo path.

        Args:
            path: Đường dẫn file

        Returns:
            Dict thông tin file hoặc None nếu không tìm thấy
        """
        if not self._conn:
            await self.init()
        async with self._conn.execute("SELECT * FROM files WHERE path = ?", (str(path),)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_file_by_id(self, file_id: int) -> dict[str, Any] | None:
        """
        Lấy thông tin file theo ID.
        """
        if not self._conn:
            await self.init()
        async with self._conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def confirm_file_and_update_path(self, file_id: int, new_path: str, search_text: str) -> None:
        """Đánh dấu file đã confirmed và cập nhật path mới."""
        if not self._conn:
            await self.init()
        await self._conn.execute(
            "UPDATE files SET confirmed = 1, path = ?, search_text = ? WHERE id = ?",
            (new_path, search_text, file_id),
        )
        await self._conn.commit()

    async def confirm_file(self, file_id: int) -> None:
        """Đánh dấu file đã được user phê duyệt (giữ nguyên path)."""
        if not self._conn:
            await self.init()
        await self._conn.execute(
            "UPDATE files SET confirmed = 1 WHERE id = ?", (file_id,)
        )
        await self._conn.commit()

    async def search(
        self,
        doc_type: str | list[str] | None = None,
        device_slug: str | None = None,
        category_slug: str | None = None,
        keyword: str | None = None,
        confirmed_only: bool = False,
        limit: int = 20,
        order_by: str = "updated_at DESC",
    ) -> list[dict[str, Any]]:
        """
        Tìm kiếm files theo các tiêu chí.

        Args:
            doc_type: Lọc theo loại tài liệu
            device_slug: Lọc theo thiết bị
            category_slug: Lọc theo category
            keyword: Tìm trong path (LIKE)
            confirmed_only: Chỉ lấy files đã confirm
            limit: Số kết quả tối đa
            order_by: Cột và chiều sắp xếp

        Returns:
            List các dict thông tin file
        """
        conditions = []
        params: list[Any] = []

        if category_slug:
            conditions.append("category_slug = ?")
            params.append(category_slug)
        if device_slug:
            conditions.append("device_slug = ?")
            params.append(device_slug)
        if doc_type:
            if isinstance(doc_type, list):
                if len(doc_type) > 0:
                    placeholders = ", ".join(["?"] * len(doc_type))
                    conditions.append(f"doc_type IN ({placeholders})")
                    params.extend(doc_type)
            else:
                conditions.append("doc_type = ?")
                params.append(doc_type)
        if keyword:
            import unidecode

            # Tìm kiếm thông minh qua search_text không dấu
            keyword_unaccented = unidecode.unidecode(keyword.lower())
            kw = f"%{keyword_unaccented}%"
            conditions.append(
                "(search_text LIKE ? OR path LIKE ? OR vendor LIKE ? OR model LIKE ? OR summary LIKE ?)"
            )
            params.extend([kw, f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if confirmed_only:
            conditions.append("confirmed = 1")

        # Validate order_by to prevent SQL injection
        # Reconstruct from whitelist — never pass raw user string to SQL
        _ALLOWED_COLUMNS = {
            "path", "sha256", "doc_type", "device_slug", "category_slug",
            "updated_at", "created_at", "indexed_at", "vendor", "model", "size_bytes",
        }
        _ALLOWED_DIRECTIONS = {"asc", "desc"}
        order_parts = order_by.lower().split()
        if len(order_parts) >= 1 and order_parts[0] in _ALLOWED_COLUMNS:
            col = order_parts[0]
            direction = order_parts[1] if len(order_parts) >= 2 and order_parts[1] in _ALLOWED_DIRECTIONS else "asc"
            order_by = f"{col} {direction.upper()}"
        else:
            order_by = "updated_at DESC"

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM files {where} ORDER BY {order_by} LIMIT ?"
        params.append(limit)

        if not self._conn:
            await self.init()
        if not self._conn:
            return []  # Should not happen after init

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_latest_by_device_and_type(
        self, device_slug: str, doc_type: str
    ) -> dict[str, Any] | None:
        """
        Lấy file mới nhất của thiết bị theo doc_type.

        Args:
            device_slug: Slug thiết bị
            doc_type: Loại tài liệu

        Returns:
            Dict thông tin file mới nhất hoặc None
        """
        results = await self.search(
            device_slug=device_slug,
            doc_type=doc_type,
            confirmed_only=True,
            limit=1,
            order_by="updated_at DESC",
        )
        return results[0] if results else None

    async def count_by_device(self, device_slug: str) -> dict[str, int]:
        """
        Đếm số file theo doc_type cho một thiết bị.

        Args:
            device_slug: Slug thiết bị

        Returns:
            Dict {doc_type: count}
        """
        if not self._conn:
            await self.init()
        if not self._conn:
            return {}

        async with self._conn.execute(
            """
            SELECT doc_type, COUNT(*) as cnt
            FROM files
            WHERE device_slug = ?
            GROUP BY doc_type
            """,
            (device_slug,),
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    async def update_file_metadata(self, file_id: int, updates: dict[str, Any]) -> None:
        """Cập nhật một hoặc nhiều cột cho file cụ thể."""
        if not updates:
            return

        _ALLOWED_UPDATE_COLUMNS = {"vendor", "model", "doc_type", "device_slug",
                                   "category_slug", "group_slug", "summary"}

        set_clauses = []
        params: list[Any] = []
        for key, value in updates.items():
            if key not in _ALLOWED_UPDATE_COLUMNS:
                raise ValueError(f"Cột không được phép cập nhật: {key}")
            set_clauses.append(f"{key} = ?")
            params.append(value)

        # Cập nhật updated_at
        set_clauses.append("updated_at = ?")
        params.append(_now_iso())

        params.append(file_id)

        sql = f"UPDATE files SET {', '.join(set_clauses)} WHERE id = ?"
        await self._conn.execute(sql, tuple(params))
        await self._conn.commit()

    async def log_event(self, event_type: str, file_path: str) -> None:
        """
        Ghi log sự kiện watcher vào DB.

        Args:
            event_type: Loại event (created, modified, deleted)
            file_path: Đường dẫn file
        """
        if not self._conn:
            await self.init()
        await self._conn.execute(
            "INSERT INTO events (event_type, file_path, ts) VALUES (?, ?, ?)",
            (event_type, file_path, _now_iso()),
        )
        await self._conn.commit()

    async def stats(self) -> dict[str, Any]:
        """
        Thống kê tổng quan index.

        Returns:
            Dict thống kê: total_files, by_doc_type, by_category
        """
        if not self._conn:
            await self.init()
        # Tổng số files
        async with self._conn.execute("SELECT COUNT(*) FROM files") as cur:
            total = (await cur.fetchone())[0]

        # Theo doc_type
        async with self._conn.execute(
            "SELECT doc_type, COUNT(*) FROM files GROUP BY doc_type"
        ) as cur:
            by_type = {row[0]: row[1] for row in await cur.fetchall()}

        # Theo category
        async with self._conn.execute(
            "SELECT category_slug, COUNT(*) FROM files WHERE category_slug IS NOT NULL GROUP BY category_slug"
        ) as cur:
            by_cat = {row[0]: row[1] for row in await cur.fetchall()}

        return {
            "total_files": total,
            "by_doc_type": by_type,
            "by_category": by_cat,
        }
