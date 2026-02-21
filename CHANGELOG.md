# Changelog

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
