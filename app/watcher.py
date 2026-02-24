"""
watcher.py — File watcher cho ~/MedicalDevices.

Theo dõi sự kiện file mới/thay đổi, debounce 3 giây,
log JSON Lines, whitelist path, bỏ qua file tạm.
Daemon không crash khi lỗi đơn lẻ.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.classifier import MedicalClassifier
from app.index_store import IndexStore

# Import logic xử lý từ process_event.py
from app.process_event import process_new_file
from app.taxonomy import Taxonomy
from app.wiki_generator import WikiGenerator

logger = logging.getLogger(__name__)


def _load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load cấu hình từ config.yaml."""
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _expand_path(path_str: str) -> Path:
    """Mở rộng ~ và biến môi trường trong path."""
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC."""
    return datetime.now(UTC).isoformat()


class EventDebouncer:
    """
    Gom nhiều events trong cửa sổ debounce thành 1 batch.

    Tránh spam khi copy nhiều file cùng lúc hoặc file lớn.
    """

    def __init__(self, debounce_seconds: float = 3.0) -> None:
        self._debounce = debounce_seconds
        # path → (event_type, timestamp)
        self._pending: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def add(self, event_type: str, path: str) -> None:
        """Thêm event vào pending queue."""
        async with self._lock:
            self._pending[path] = (event_type, time.monotonic())

    async def flush(self) -> list[dict[str, Any]]:
        """
        Lấy các events đã qua debounce window.

        Returns:
            List events sẵn sàng xử lý
        """
        now = time.monotonic()
        ready = []
        async with self._lock:
            expired_keys = [
                path for path, (_, ts) in self._pending.items() if now - ts >= self._debounce
            ]
            for path in expired_keys:
                event_type, _ = self._pending.pop(path)
                ready.append({"event": event_type, "path": path})
        return ready


class MedicalFileHandler(FileSystemEventHandler):
    """
    Xử lý sự kiện file từ watchdog.

    Lọc file tạm, whitelist path, đưa vào event queue.
    """

    def __init__(
        self,
        root_path: Path,
        ignore_patterns: list[str],
        allowed_extensions: list[str],
        min_size_bytes: int,
        event_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._root = root_path
        self._ignore_patterns = ignore_patterns
        self._allowed_extensions = {ext.lower() for ext in allowed_extensions}
        self._min_size = min_size_bytes
        self._queue = event_queue
        self._loop = loop

    def _should_ignore(self, path: str) -> bool:
        """Kiểm tra file có nên bỏ qua không."""
        p = Path(path)
        name = p.name
        # Kiểm tra ignore patterns bằng fnmatch
        for pattern in self._ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        # Kiểm tra whitelist extension
        if p.suffix.lower() not in self._allowed_extensions:
            logger.info(f"🔬 DEBUG WATCHER: {p.suffix.lower()} not in whitelist")
            return True
            
        # Kiểm tra whitelist path
        try:
            p.relative_to(self._root)
        except ValueError:
            logger.warning("Path ngoài whitelist, bỏ qua: %s", path)
            return True
        return False

    def _is_valid_file(self, path: str) -> bool:
        """Kiểm tra file tồn tại và đủ kích thước."""
        try:
            size = os.path.getsize(path)
            return size >= self._min_size
        except OSError:
            return False

    def _enqueue(self, event_type: str, path: str) -> None:
        """Đưa event vào async queue (thread-safe)."""
        logger.info(f"🔎 DEBUG WATCHER: Caught {event_type} on {path}")
        
        if self._should_ignore(path):
            logger.info(f"🚫 DEBUG WATCHER: Ignored by _should_ignore: {path}")
            return
        if event_type in ("created", "modified") and not self._is_valid_file(path):
            logger.info(f"🚫 DEBUG WATCHER: Invalid file size or not found: {path} (size >={self._min_size} required)")
            return

        logger.info(f"✅ DEBUG WATCHER: Enqueued {path}")

        event = {
            "event": event_type,
            "path": path,
            "ts": _now_iso(),
            "size_bytes": self._get_size(path),
        }
        # Thread-safe: gọi từ watchdog thread sang asyncio loop
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    def _get_size(self, path: str) -> int:
        """Lấy kích thước file, trả 0 nếu lỗi."""
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue("created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue("modified", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue("created", event.dest_path)


class MedicalWatcher:
    """
    Daemon theo dõi ~/MedicalDevices và xử lý events.

    Ví dụ sử dụng:
        watcher = MedicalWatcher("config.yaml")
        await watcher.run()
    """

    def __init__(self, config_path: str = "config.yaml") -> None:
        self._config = _load_config(config_path)
        self._root = _expand_path(self._config["paths"]["medical_devices_root"])
        self._log_dir = _expand_path(self._config["paths"]["log_dir"])
        self._debounce = self._config["watcher"]["debounce_seconds"]
        self._ignore = self._config["watcher"]["ignore_patterns"]
        self._min_size = self._config["watcher"]["min_file_size_bytes"]
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._debouncer = EventDebouncer(self._debounce)
        self._running = False

        # Services
        self._classifier = None
        self._store = None
        self._wiki = None
        self._taxonomy = None

    async def _init_services(self) -> None:
        """Khởi tạo các dịch vụ cần thiết."""
        self._classifier = MedicalClassifier("config.yaml")
        self._store = IndexStore(self._config["paths"]["db_file"])
        await self._store.init()
        self._wiki = WikiGenerator("config.yaml")
        self._taxonomy = Taxonomy(self._config["paths"]["taxonomy_file"])
        logger.info("✅ Đã khởi tạo các dịch vụ (Classifier, Store, Wiki, Taxonomy)")

    def _setup_logging(self) -> None:
        """Cấu hình logging JSON Lines."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._log_dir / "watcher.jsonl"

        # Handler ghi file JSON Lines
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def _log_event(self, event: dict[str, Any]) -> None:
        """Ghi event ra log file JSON Lines."""
        log_file = self._log_dir / "watcher.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    async def _process_event(self, event: dict[str, Any]) -> None:
        """
        Xử lý một event file.

        Hiện tại: log event. Phase 2 sẽ gọi classifier + bot.
        """
        try:
            self._log_event(event)
            logger.info(
                "📄 Event: %s — %s (%d bytes)",
                event["event"],
                Path(event["path"]).name,
                event.get("size_bytes", 0),
            )

            # Gọi logic xử lý Phase 1.0 (Classify -> Move -> DB -> Wiki -> Notify)
            # Lưu ý macOS: cp/copy file thường tạo sự kiện 'modified' thay vì 'created'
            if event["event"] in ("created", "modified", "moved"):
                await process_new_file(
                    event["path"],
                    self._config,
                    self._classifier,
                    self._store,
                    self._wiki,
                    self._taxonomy,
                )

        except Exception as e:
            # Không crash daemon
            logger.error("Lỗi xử lý event %s: %s", event.get("path"), e)

    async def _consumer(self) -> None:
        """Vòng lặp consumer: lấy events từ queue, debounce, xử lý."""
        while self._running:
            try:
                # Lấy event từ queue (timeout để kiểm tra running)
                try:
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self._debouncer.add(event["event"], event["path"])
                    # Cập nhật size/ts từ event gốc
                except TimeoutError:
                    pass

                # Flush events đã qua debounce window
                ready_events = await self._debouncer.flush()
                for evt in ready_events:
                    # Lấy lại size từ file thực tế
                    try:
                        evt["size_bytes"] = os.path.getsize(evt["path"])
                    except OSError:
                        evt["size_bytes"] = 0
                    evt["ts"] = _now_iso()
                    await self._process_event(evt)

            except Exception as e:
                logger.error("Lỗi consumer loop: %s", e)
                await asyncio.sleep(1)

    async def run(self) -> None:
        """Khởi động watcher daemon."""
        self._setup_logging()

        if not self._root.exists():
            logger.warning("Thư mục chưa tồn tại, tạo mới: %s", self._root)
            self._root.mkdir(parents=True, exist_ok=True)

        logger.info("🚀 MedicalWatcher khởi động")
        logger.info("📁 Watch path: %s", self._root)
        logger.info("⏱️  Debounce: %ss", self._debounce)

        loop = asyncio.get_running_loop()
        handler = MedicalFileHandler(
            root_path=self._root,
            ignore_patterns=self._ignore,
            allowed_extensions=self._config["watcher"]["allowed_extensions"],
            min_size_bytes=self._min_size,
            event_queue=self._event_queue,
            loop=loop,
        )

        observer = Observer()
        observer.schedule(handler, str(self._root), recursive=True)
        observer.start()
        self._running = True

        # Xử lý Ctrl+C
        def _shutdown(sig, frame):
            logger.info("🛑 Nhận signal %s, dừng watcher...", sig)
            self._running = False
            observer.stop()

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            await self._init_services()
            await self._consumer()
        finally:
            if self._store:
                await self._store.close()
            observer.stop()
            observer.join()
            logger.info("✅ Watcher đã dừng")


def main() -> None:
    """Entry point cho watcher daemon."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    watcher = MedicalWatcher(config_path)
    asyncio.run(watcher.run())


if __name__ == "__main__":
    main()
