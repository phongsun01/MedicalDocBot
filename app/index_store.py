"""
index_store.py — SQLite index cho tài liệu thiết bị y tế.

Lưu trữ metadata file: path, sha256, doc_type, device_slug,
category_slug, timestamps. Hỗ trợ async với aiosqlite.
Idempotent: upsert theo path (không tạo duplicate).
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

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
    return datetime.now(timezone.utc).isoformat()


def compute_sha256(file_path: str | Path) -> str:
    """
    Tính SHA256 của file.

    Args:
        file_path: Đường dẫn file

    Returns:
        Chuỗi hex SHA256
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


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

    async def init(self) -> None:
        """Tạo schema nếu chưa có."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(_SCHEMA_SQL)
            await db.commit()
        logger.info("IndexStore khởi tạo: %s", self._db_path)

    async def upsert_file(
        self,
        path: str | Path,
        sha256: str,
        doc_type: str = "khac",
        device_slug: str | None = None,
        category_slug: str | None = None,
        group_slug: str | None = None,
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

        async with aiosqlite.connect(self._db_path) as db:
            # Kiểm tra đã tồn tại chưa
            async with db.execute(
                "SELECT id, created_at FROM files WHERE path = ?", (path_str,)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                # Cập nhật record hiện có
                await db.execute(
                    """
                    UPDATE files SET
                        sha256 = ?, doc_type = ?, device_slug = ?,
                        category_slug = ?, group_slug = ?,
                        size_bytes = ?, confirmed = ?, updated_at = ?, indexed_at = ?
                    WHERE path = ?
                    """,
                    (
                        sha256, doc_type, device_slug,
                        category_slug, group_slug,
                        size_bytes, int(confirmed), now, now,
                        path_str,
                    ),
                )
                record_id = existing[0]
                logger.debug("Cập nhật file: %s (id=%d)", path_str, record_id)
            else:
                # Thêm record mới
                cursor = await db.execute(
                    """
                    INSERT INTO files
                        (path, sha256, doc_type, device_slug, category_slug, group_slug,
                         size_bytes, confirmed, created_at, updated_at, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        path_str, sha256, doc_type, device_slug,
                        category_slug, group_slug,
                        size_bytes, int(confirmed), now, now, now,
                    ),
                )
                record_id = cursor.lastrowid
                logger.debug("Thêm file mới: %s (id=%d)", path_str, record_id)

            await db.commit()

        return record_id
    
    async def delete_file(self, path: str | Path) -> None:
        """
        Xóa file khỏi index.
        
        Args:
            path: Đường dẫn file cần xóa
        """
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM files WHERE path = ?", (str(path),))
            await db.commit()
            logger.info("Đã xóa file khỏi DB: %s", path)

    async def get_file(self, path: str | Path) -> dict[str, Any] | None:
        """
        Lấy thông tin file theo path.

        Args:
            path: Đường dẫn file

        Returns:
            Dict thông tin file hoặc None nếu không tìm thấy
        """
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM files WHERE path = ?", (str(path),)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def search(
        self,
        doc_type: str | None = None,
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

        if doc_type:
            conditions.append("doc_type = ?")
            params.append(doc_type)
        if device_slug:
            conditions.append("device_slug = ?")
            params.append(device_slug)
        if category_slug:
            conditions.append("category_slug = ?")
            params.append(category_slug)
        if keyword:
            conditions.append("path LIKE ?")
            params.append(f"%{keyword}%")
        if confirmed_only:
            conditions.append("confirmed = 1")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM files {where} ORDER BY {order_by} LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
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
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
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

    async def log_event(self, event_type: str, file_path: str) -> None:
        """
        Ghi log sự kiện watcher vào DB.

        Args:
            event_type: Loại event (created, modified, deleted)
            file_path: Đường dẫn file
        """
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO events (event_type, file_path, ts) VALUES (?, ?, ?)",
                (event_type, file_path, _now_iso()),
            )
            await db.commit()

    async def stats(self) -> dict[str, Any]:
        """
        Thống kê tổng quan index.

        Returns:
            Dict thống kê: total_files, by_doc_type, by_category
        """
        async with aiosqlite.connect(self._db_path) as db:
            # Tổng số files
            async with db.execute("SELECT COUNT(*) FROM files") as cur:
                total = (await cur.fetchone())[0]

            # Theo doc_type
            async with db.execute(
                "SELECT doc_type, COUNT(*) FROM files GROUP BY doc_type"
            ) as cur:
                by_type = {row[0]: row[1] for row in await cur.fetchall()}

            # Theo category
            async with db.execute(
                "SELECT category_slug, COUNT(*) FROM files WHERE category_slug IS NOT NULL GROUP BY category_slug"
            ) as cur:
                by_cat = {row[0]: row[1] for row in await cur.fetchall()}

        return {
            "total_files": total,
            "by_doc_type": by_type,
            "by_category": by_cat,
        }
