"""
watcher.py — File system watcher cho ~/MedicalDevices
Dùng watchdog để theo dõi thay đổi file, debounce 3s, gửi vào event queue.
Mọi lỗi được log JSON, không crash daemon.
"""

import json
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import (
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from app.config import BASE_DIR, WATCHER_DEBOUNCE_SECONDS, setup_logging
from app.index_store import compute_sha256, init_db, log_event, upsert_file

logger = logging.getLogger("medicalbot.watcher")

# Các extension file được theo dõi
WATCHED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".pptx", ".ppt", ".jpg", ".jpeg", ".png",
    ".zip", ".rar", ".7z",
}

# Thư mục bỏ qua (cache, db, hidden)
IGNORED_DIRS = {".cache", ".db", "__pycache__", ".git", "wiki"}


def _should_watch(path: Path) -> bool:
    """Kiểm tra file có nên được theo dõi không."""
    # Bỏ qua hidden files
    if path.name.startswith("."):
        return False
    # Bỏ qua thư mục đặc biệt
    for part in path.parts:
        if part in IGNORED_DIRS:
            return False
    # Chỉ theo dõi extension được phép
    return path.suffix.lower() in WATCHED_EXTENSIONS


class _DebounceTimer:
    """
    Timer debounce: chờ DEBOUNCE_SECONDS sau event cuối cùng rồi mới xử lý.
    Tránh spam khi copy file lớn (nhiều modified events liên tiếp).
    """

    def __init__(self, delay: float, callback: Callable[[str], None]) -> None:
        self._delay = delay
        self._callback = callback
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def trigger(self, path: str) -> None:
        """Kích hoạt debounce cho path. Reset timer nếu đã có."""
        with self._lock:
            if path in self._timers:
                self._timers[path].cancel()
            timer = threading.Timer(self._delay, self._fire, args=[path])
            self._timers[path] = timer
            timer.start()

    def _fire(self, path: str) -> None:
        """Gọi callback sau khi debounce xong."""
        with self._lock:
            self._timers.pop(path, None)
        try:
            self._callback(path)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {"op": "debounce_fire", "path": path, "error": str(exc)},
                    ensure_ascii=False,
                )
            )

    def cancel_all(self) -> None:
        """Hủy tất cả timers đang chờ."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()


class MedicalDocHandler(FileSystemEventHandler):
    """
    Xử lý file system events từ watchdog.
    Debounce 3s trước khi đưa vào event queue.
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        debounce_seconds: float = WATCHER_DEBOUNCE_SECONDS,
    ) -> None:
        super().__init__()
        self._queue = event_queue
        self._debouncer = _DebounceTimer(debounce_seconds, self._enqueue)
        self._pending_event_type: dict[str, str] = {}  # path → event_type
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if _should_watch(path):
            with self._lock:
                self._pending_event_type[str(path)] = "created"
            self._debouncer.trigger(str(path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if _should_watch(path):
            with self._lock:
                # Không ghi đè "created" bằng "modified"
                if str(path) not in self._pending_event_type:
                    self._pending_event_type[str(path)] = "modified"
            self._debouncer.trigger(str(path))

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if _should_watch(dest):
            with self._lock:
                self._pending_event_type[str(dest)] = "created"
            self._debouncer.trigger(str(dest))

    def _enqueue(self, path_str: str) -> None:
        """Đưa event vào queue sau debounce."""
        with self._lock:
            event_type = self._pending_event_type.pop(path_str, "modified")
        path = Path(path_str)
        if path.exists():
            self._queue.put({"type": event_type, "path": path_str})
            logger.info("Event queued: [%s] %s", event_type, path.name)


class FileEventProcessor(threading.Thread):
    """
    Worker thread xử lý events từ queue.
    Gọi index_store.upsert_file() + log_event() + optional callback.
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        on_new_file: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(daemon=True, name="FileEventProcessor")
        self._queue = event_queue
        self._on_new_file = on_new_file  # callback(path, sha256)
        self._stop_event = threading.Event()

    def run(self) -> None:
        logger.info("FileEventProcessor bắt đầu chạy")
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=1.0)
                self._process(event)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as exc:
                logger.error(
                    json.dumps(
                        {"op": "processor_run", "error": str(exc)},
                        ensure_ascii=False,
                    )
                )

    def _process(self, event: dict) -> None:
        """Xử lý một event: index file + log."""
        path_str = event["path"]
        event_type = event["type"]
        path = Path(path_str)

        try:
            if not path.exists():
                logger.warning("File không còn tồn tại: %s", path_str)
                return

            # Tính sha256 + upsert vào DB
            sha256 = upsert_file(path)

            # Log event
            log_event(event_type, path_str, sha256)

            logger.info(
                "Đã xử lý [%s] %s (sha256=%s)",
                event_type,
                path.name,
                sha256[:8],
            )

            # Gọi callback nếu có (vd: trigger classifier)
            if self._on_new_file and event_type in ("created", "modified"):
                try:
                    self._on_new_file(path_str, sha256)
                except Exception as cb_exc:
                    logger.error(
                        json.dumps(
                            {"op": "on_new_file_callback", "path": path_str, "error": str(cb_exc)},
                            ensure_ascii=False,
                        )
                    )

        except Exception as exc:
            logger.error(
                json.dumps(
                    {"op": "process_event", "path": path_str, "event_type": event_type, "error": str(exc)},
                    ensure_ascii=False,
                )
            )

    def stop(self) -> None:
        self._stop_event.set()


class MedicalDocWatcher:
    """
    Watcher chính: khởi động watchdog Observer + FileEventProcessor.
    Interface đơn giản: start() / stop().
    """

    def __init__(
        self,
        watch_dir: Path = BASE_DIR,
        on_new_file: Optional[Callable[[str, str], None]] = None,
        debounce_seconds: float = WATCHER_DEBOUNCE_SECONDS,
    ) -> None:
        self._watch_dir = watch_dir
        self._event_queue: queue.Queue = queue.Queue()
        self._handler = MedicalDocHandler(self._event_queue, debounce_seconds)
        self._observer = Observer()
        self._processor = FileEventProcessor(self._event_queue, on_new_file)

    def start(self) -> None:
        """Khởi động watcher."""
        init_db()
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        self._observer.schedule(self._handler, str(self._watch_dir), recursive=True)
        self._observer.start()
        self._processor.start()
        logger.info("Watcher đang theo dõi: %s", self._watch_dir)

    def stop(self) -> None:
        """Dừng watcher gracefully."""
        self._handler._debouncer.cancel_all()
        self._observer.stop()
        self._observer.join()
        self._processor.stop()
        logger.info("Watcher đã dừng")

    def run_forever(self) -> None:
        """Chạy watcher cho đến khi nhận KeyboardInterrupt."""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Nhận Ctrl+C, đang dừng watcher...")
        finally:
            self.stop()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    setup_logging()
    logger.info("=== MedicalDocBot Watcher ===")
    logger.info("Thư mục theo dõi: %s", BASE_DIR)
    watcher = MedicalDocWatcher()
    watcher.run_forever()
