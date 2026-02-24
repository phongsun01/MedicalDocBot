# Changelog
 
## [2.7.4] - 2026-02-24
### Fixed
- **Bot**: Cải thiện độ ổn định Telegram bot, sửa lỗi Markdown bị lẫn trong HTML (Commands: `latest`, `find`, `status`) (BUG #1, #2, #7, #8).
- **Bot**: Thêm `try/catch` qua hàm `_safe_edit_markup` để sửa lỗi thiếu handling khi user nhấn `edit_type` (BUG #11).
- **Bot**: Đưa `logging.basicConfig` vào `main` để tránh config ở cấp module (BUG #3).
- **Core**: Sửa lỗi `update_file_metadata` gọi `self.init()` vô điều kiện (BUG #4).
- **Core**: Sửa race condition lock cấp class trong `classifier.py` bằng cách đưa xuống cấp object instance (BUG #5).
- **Config**: Cập nhật lại tên model AI 9router từ `openrouter/auto` sang `if/glm-4.7` hợp lệ (BUG #6).
- **Process**: Loại bỏ import thừa `escape_markdown` nhằm làm gọn mã nguồn (BUG #9).
- **Tests**: Khắc phục các test assert do sai thứ tự tham số hoặc escape HTML (BUG #12, #13).

## [2.7.3] - 2026-02-24
### Fixed
- **Core**: Sửa lỗi `AttributeError` khi gọi `init_db()` thay vì `init()` trong `index_store.py`.
- **Bot**: Sửa lỗi chồng chéo (shadowing) biến `store` trong các hàm callback của Telegram.
- **Bot**: Thêm `html.escape` cho tên tệp khi gửi tài liệu để tránh lỗi cú pháp HTML.
- **Watcher**: Thay thế `asyncio.get_event_loop()` (đã lỗi thời) bằng `asyncio.get_running_loop()`.
- **Search**: Đổi tên `DOC_TYPE_MAP` thành `KEYWORD_TO_DOC_TYPE` để tránh trùng tên và bổ sung từ khóa tìm kiếm.
- **Classifier**: Cải thiện logic bắt ngoại lệ (exception handling) để xử lý retry chính xác hơn.
- **Process**: Cải thiện việc tách tên hãng (vendor) và model từ slug thiết bị.
- **Wiki**: Tối ưu hóa phạm vi biến trong trình tạo mục lục Wiki.
- **Tests**: Cập nhật fixture bộ test và bổ sung `test_v272_fixes.py` để kiểm tra các bản vá.


## [2.7.2] - 2026-02-24
### Fixed
- **Critical**: Tuple unpacking error in `build_device_slug()` when used in `telegram_bot.py`.
- **Critical**: `MedicalClassifier` lock initialization moved inside coroutine to bind to correct asyncio event loop.
- **Security**: Added explicit column allowlist for `update_file_metadata()` to prevent SQL injection.
- **Security**: Fixed type mismatch (`int` vs `str`) in Telegram `/send` access control.
- **Reliability**: Ensured `awaiting_input` state is always cleared in `finally` blocks.
- **UI**: Corrected HTML escaping for error messages in file sending flow.
- **Refactoring**: Removed unused `huong_dan_su_dung` mapping and dead imports.

## [2.7.1] - 2026-02-24
### Fixed
- **Security**: Fixed a potential SQL injection vulnerability in `IndexStore.search` handling of the `order_by` clause by enforcing strict whitelist-based reconstruction.
- **Security**: Added strict access control to the Telegram `/send` command to prevent unauthorized file downloads. Access is now restricted to the target `group_chat_id`, the specified `admin_chat_id`, and a configurable `allowed_users` list.
- **Core**: Resolved unreliable thread-safety in `classifier.py`'s `_request_lock` initialization.
- **Core**: Fixed duplicate calls to `WikiGenerator.generate_indexes` during the UI inline approval flow.
- **Core**: Centralized definition of `CATEGORY_MAP` and `GROUP_MAP` in `process_event.py` for performance. 
- **Misc**: Replaced hardcoded root paths with configurations pulled dynamically from `config.yaml` to improve cross-platform portability.
- **Misc**: Cleaned up minor regex boundaries in `search.py` and duplicate mappings in `slug.py`.


## [2.7.0] - 2026-02-24

### Added
- **UC2 Edit Classification Flow**: Implemented the full Telegram inline edit experience.
  - Tapping "✏️ Chỉnh sửa" now shows a submenu with 3 editable field buttons (Hãng, Model, Loại) and a Back button.
  - **Sửa Hãng / Sửa Model**: Bot sends a `ForceReply` prompt. User replies with the new value. Bot updates DB, recalculates `device_slug`, deletes the reply clutter, and refreshes the original draft message.
  - **Sửa Loại**: Bot shows a 2-column `InlineKeyboardMarkup` with 9 document types. Bot updates DB on tap and refreshes draft.
  - Back button restores original approve/edit keyboard.
- **`app/ui.py` (NEW)**: Shared rendering module — `render_draft_message`, `render_edit_menu`, `render_type_selection_menu`. Used by both `process_event.py` and `telegram_bot.py` to eliminate HTML duplication.
- **`IndexStore.update_file_metadata`**: New atomic method to update multiple DB columns in one query.
- **`_safe_edit`**: Added `reply_markup` parameter to support refreshing interactive keyboards.

### Changed
- `process_event.py`: Now uses `render_draft_message` from `app.ui` instead of hardcoded HTML strings.
- `telegram_bot.py`: Added `_refresh_draft_message` helper; `handle_message` now intercepts ForceReply before generic auto-search.

---

## [2.6.4] - 2026-02-24

### Fixed
- **`_send_file_to_user` (large file path)**: Applied `html.escape` to `file_path` in "file too large" error message and corrected `<50MB` literal to `&lt;50MB` to prevent HTML injection.
- **`button_callback` (approve error)**: Applied `html.escape(str(e))` on exception message before embedding in Telegram HTML reply — prevents `BadRequest` when OS/path errors contain `<`, `>`, or `&`.
- **`MedicalClassifier` docstring**: Updated stale "Gemini" reference to "9router local gateway" to accurately reflect the actual AI backend.

---

## [2.6.3] - 2026-02-24

### Fixed
- **`status_command`**: Removed remaining `ParseMode.MARKDOWN` reference; exception path now wraps error string with `html.escape` to prevent `BadRequest` on special characters.
- **`_send_file_to_user`**: Applied `html.escape` on filename before embedding in HTML bold tag.
- **`edit_` callback**: Replaced unsafe `query.message.reply_text` (crashes if message is deleted) with `_safe_edit` wrapper.
- **`classifier.py`**: Changed `load_dotenv()` to `load_dotenv(override=False)` to prevent environment variable pollution when module is imported in tests.

---

## [2.6.2] - 2026-02-24

### Fixed
- **Bot Crash Loop**: Added `_safe_edit` helper to prevent unhandled Telegram API exceptions if `edit_message_text` raises due to identical messages.
- **Race Condition in File Sync**: Reordered `shutil.move` to execute *before* `confirm_file_and_update_path` to prevent Database path updates without successful physical file moves.
- **Data Corruption**: Removed redundant `confirm_file` call before `confirm_file_and_update_path` which caused the Database to save the old path instead of the new categorized path.
- **UI Markdown Formatting**: Switched all bot message outputs (including `/status`, `/find`, `/latest`) to `ParseMode.HTML` wrapped with `html.escape` to resolve unrendered `**bold**` tags and API exceptions caused by unescaped backticks.
- **Service Stability**: Implemented `is_connected()` abstraction for SQLite checking instead of unsafe private member access.
- **Startup Errors**: Handled `RuntimeError` gracefully when initializing database `_backfill` outside of an active asyncio event loop.
- **Environment Side-effects**: Re-scoped `load_dotenv` and `logging.basicConfig` to the CLI entry point to prevent test environment pollution when importing `process_event`.

---

## [2.6.1] - 2026-02-24

### Fixed
- **Telegram UI Robustness**: Wrapped `edit_message_text` in a try-except block and added a high-resolution timestamp to approval messages to prevent "Message is not modified" errors from the Telegram API when multiple actions target the same document.

---

## [2.6.0] - 2026-02-23

### Added
- **UC1 Full Confirmation Flow**: Clicking "✅ Phê duyệt" on Telegram now physically moves the file from the root directory into the appropriate taxonomy-based folder structure (e.g., `Category/Group/Device/filename.pdf`).
- **Real-time Wiki Sync**: Approved files now trigger an immediate run of `WikiGenerator` to update the specific Device Wiki page and rebuild the global `00_Index.md` in Obsidian.
- **Enhanced Watcher Logging**: Added debug logs within the watcher pipeline to track ignored files and valid event enqueuing for easier troubleshooting.

### Fixed
- **Regex Filter False Positives**: Replaced imprecise regex logic in `watcher.py` with `fnmatch` to prevent clinical document filenames containing "Catalog" from being erroneously blocked by the `*.log` filter.

---

## [2.5.1] - 2026-02-23

### Fixed
- **Markdown vs HTML mixing in Telegram Bot**: Fixed crash issues occurring when naming schemes clashed with Markdown in `/latest`, `/find`, system errors, and `approve` callback handlers by standardizing completely on HTML strings and `html.escape`. (Fixes Bug #1, #2, #5, #6).
- **IndexStore DB Encapsulation**: Refactored `telegram_bot.py` to use `IndexStore.confirm_file` and `IndexStore.confirm_file_and_update_path`. Absolute elimination of direct `_conn` accesses. (Fixes Bug #3, #4).
- **Sub-word matching in Search Regex**: Replaced generic Python regex `\b` with robust word boundaries `(^|\s)` for reliable unicode Vietnamese partial keyword stripping in `search.py`. (Fixes Bug #7).
- **9Router Initial Config Name**: Replaced invalid "openrouter/auto" string in `config.yaml` with the actually functional "if/glm-4.7" local prefix. (Fixes Bug #8).
- **Wiki Generator Double Newlines**: Removed excess spacing by utilizing `"".join()` when combining `\n`-postfixed strings. (Fixes Bug #9).
- **Watcher Non-Document Filtering**: Updated `config.yaml` with an explicit `allowed_extensions` list and enforced it within `watcher.py` to prevent reading IDE configurations as medical files (e.g. `workspace.json`).

---

## [2.5.0] - 2026-02-23

### Added
- **Confirm Flow (UC1)**: All newly detected documents are now stored as DRAFT (`confirmed=False`) and presented to users on Telegram with **✅ Phê duyệt** / **✏️ Chỉnh sửa** buttons. Files are only moved and wiki is only updated after explicit user approval. This aligns with the UC1 spec.
- **Multi doc_type Search**: `search.py` now extracts all doc_type keywords from a query (e.g. "cấu hình hợp đồng GE" → filters both `cau_hinh` AND `hop_dong`), eliminating the single-match `break` bug.
- **`get_file_by_id` on IndexStore**: Added a proper public method to retrieve file records by ID, eliminating direct `_conn` access from `telegram_bot.py`.
- **New Unit Tests**: Added `tests/test_search.py` (4 cases for query parsing) and `tests/test_classifier.py` (mocked API call) — total test suite is now 16 tests, all passing.

### Fixed
- **`IndexStore.search()` ignored `doc_type`**: The filter condition for `doc_type` was never appended to `conditions`. Now supports both `str` and `list[str]` (uses `IN (...)`).
- **Telegram 400 Bad Request (MarkdownV2)**: Switched all `sendMessage` calls from `MARKDOWN_V2` to `HTML` mode and used `html.escape()` for all dynamic content. Eliminates errors from `(`, `)`, `.`, `!` in vendor/summary text.
- **`handle_message()` group spam**: Auto-search on non-command messages is now restricted to private chats only. Group chat messages no longer trigger search results.
- **`classifier.py` outdated docstring**: Updated module docstring from "Gemini Generative AI" to "9router local gateway".
- **Rate limiting hardcoded to 6s**: Rate limit delay now reads from `config['services']['9router']['rate_limit_seconds']` (default: 6.0). Configurable without touching code.
- **`search_text` backfill blocks startup**: Moved the per-row UPDATE loop in `IndexStore.init()` to an `asyncio.create_task(_backfill())` background coroutine using `executemany`. Startup is no longer blocked on large databases.
- **`start()` mixing Markdown in HTML reply**: Removed `**bold**` Markdown syntax from `reply_html()` in favor of proper `<b>` HTML tags.

---

## [2.4.0] - 2026-02-22

### Added
- **Smart Search (`/find`)**: Implemented an intelligent parser `app/search.py` that identifies Vietnamese `doc_type` keywords (e.g. "cấu hình", "hợp đồng") explicitly from user queries, coupled with a seamless Telegram `/find` integration.
- **Direct File Downloads (`/send`)**: Users can now directly download physical documents via Telegram Inline Keyboards automatically attached under search results. Included a 50MB fallback for Telegram's file limit.
- **Unaccented Vietnamese Search**: Upgraded the `IndexStore` database to maintain a `search_text` column containing lowered, unaccented document information (via `unidecode`). This guarantees robust search hit-rates regardless of tone marks (e.g. "den mo", "ban mo", "xquang").

### Fixed
- **OpenClaw Token Conflict**: Documented and guided the isolation of the `openclaw` daemon's Telegram bot token to resolve cross-application message stealing conflicts.## [2.3.2] - 2026-02-22
### Fixed
- **Robust JSON Parsing**: Upgraded `classifier.py` to use `json.JSONDecoder().raw_decode()` to extract valid JSON even when OpenRouter or proxy models append trailing garbage characters (e.g. `Server-Sent Events` data or `data: [DONE]`).
- **Duplicate Event Suppression**: Refactored `process_event.py` to perform an early `store.get_file(file_path)` check. This permanently fixes the infinite feedback loop where `watcher.py` would catch its own subfolder `move` events and double-process already categorized files, resulting in false-positive duplicate error messages to Telegram.


### Fixed
- **Telegram Bot**: 
    - Replaced non-existent `count_files` method with `stats()["total_files"]` for the `/status` command.
    - Updated AI Model configuration reference from `gemini` to `9router`.
    - Refactored global `store` state to use context-safe `app.bot_data["store"]`.
- **Wiki Generator**: 
    - Removed unused `store` parameter from `generate_indexes` to prevent confusion.
    - Updated `test_wiki_generator.py` assertions to align with the new `00_Danh_muc_thiet_bi` root folder structure.


 ## [2.3.0] - 2026-02-22
 
 ### Added
 - **Content-Based Classification**: Integrated `kreuzberg` to extract document text (first 3000 chars), significantly improving AI classification accuracy for vendors, models, and categories.
 - **Shared Utilities**: Centralized hashing and sanitization logic in `app/utils.py`.
 
 ### Changed
 - **Architectural Refactoring**: 
     - Applied Dependency Injection in `process_event.py` and `watcher.py` for core services.
     - `IndexStore` now uses a persistent database connection for better performance.
     - Switched to `ParseMode.MARKDOWN_V2` for Telegram notifications with improved character escaping.
 - **Data Integrity**: Enforced strict SHA256 hashing; the system now stops if integrity checks fail.
 - **Wiki Improvement**: `WikiGenerator` now correctly filters index files using `00_Index.md` convention.
 
 ### Fixed
 - Missing `Any` and `Dict` imports in `MedicalClassifier`.
 - Asynchronous initialization issue with `_request_lock` in `MedicalClassifier`.
 

## [2.2.0] - 2026-02-22

### Added
- **9router Integration**: Migrated the classifier from Google Gemini API to the local 9router gateway (port 20128).
- OpenAI-compatible API support using `httpx` for efficient AI communications.
- Native support for multiple local/cloud models via 9router (e.g., Qwen, Claude, Gemini).

### Changed
- Refactored `app/classifier.py` to remove `google-generativeai` dependency.
- Updated `config.yaml` and `.env` to center around 9router settings.
- Improved Error Handling with exponential backoff for HTTP 429 and connection issues.

## [2.1.2] - 2026-02-20

### Added
- Created `scripts/full_regen.py` for comprehensive wiki index and page regeneration.
- Created `scripts/deep_cleanup.py` for robust removal of legacy index files.
- New folder-based root index structure in Wiki (`00_Danh_muc_thiet_bi/00_Index.md`).

### Changed
- **Wiki Navigation**: Renamed all `!Index.md` files to `00_Index.md` to force top-sorting in Obsidian regardless of "Folders first" settings.
- **Taxonomy Refinement**: 
    - Standardized all hyphens to standard `-` for better filesystem compatibility.
    - Fixed Vietnamese spelling for "Tim mạch" and category grouping for Surgery.
    - Aligned `thiet_bi_phong_mo` slug across classifier, database, and taxonomy.
- **Documentation**: Updated `TELEGRAM_GUIDE.md` to reflect that `group_chat_id` is now configured in `config.yaml`, not hardcoded in Python.

### Fixed
- Fixed inconsistent sorting in Obsidian sidebar by moving from character-based (`!`) to folder-based (`00_`) priority.
- Cleaned up 144+ legacy index files that were cluttering the Wiki.
