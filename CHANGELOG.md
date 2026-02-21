# Changelog
 
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
