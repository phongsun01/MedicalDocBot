import asyncio
import html
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from app.classifier import MedicalClassifier
from app.index_store import IndexStore
from app.slug import build_device_slug
from app.taxonomy import Taxonomy
from app.utils import clean_name, compute_sha256
from app.wiki_generator import WikiGenerator
from app.ui import DOC_TYPE_MAP, render_draft_message

load_dotenv(override=False)

logger = logging.getLogger(__name__)

# Helper functions moved or removed (Dependency Injection used instead)

# DOC_TYPE_MAP moved to app.ui

# clean_name moved to app.utils

# Correction maps for AI hallucinations — module-level constants (created once)
_CATEGORY_MAP: dict[str, str] = {
    "ngoai_khoa": "thiet_bi_phong_mo",
    "phau_thuat": "thiet_bi_phong_mo",
    "phong_mo": "thiet_bi_phong_mo",
    "trang_thiet_bi_phong_mo": "thiet_bi_phong_mo",
    "thiet-bi-phong-mo": "thiet_bi_phong_mo",
    "thiet_bi_hoi_suc": "hoi_suc_cap_cuu",
    "thiet_bi_hoi_suc_gay_me": "gay_me_may_tho",
    "Unknown": "chua_phan_loai",
    "khac": "chua_phan_loai",
}

_GROUP_MAP: dict[str, str] = {
    "Unknown": "khac",
    "may_tho": "may_tho_hoi_suc",
    "phong_mo": "khac",
    "thiet_bi_phong_mo": "khac",
    "ban-mo": "ban_mo",
    "monitor_benh_nhan": "monitor",
    "may_theo_doi_benh_nhan": "monitor",
    "bon_rua_tay_phau_thuat": "bon_rua_tay",
}



def detect_manual_placement(file_path: str, config: dict) -> dict | None:
    """
    Checks if a file is already placed in a valid taxonomy folder.
    Returns metadata if detected, else None.
    Structure: ROOT / category / group / device / doc_type_folder / filename
    """
    try:
        root_path = Path(os.path.expandvars(os.path.expanduser(config["paths"]["medical_devices_root"]))).resolve()
        file_path_obj = Path(file_path).resolve()
        
        if not str(file_path_obj).startswith(str(root_path)):
            return None
            
        rel_parts = file_path_obj.relative_to(root_path).parts
        
        # Expected: (category, group, device, sub_dir, filename) -> length 5
        if len(rel_parts) != 5:
            return None
            
        category_slug, group_slug, device_slug, sub_dir, filename = rel_parts
        
        # Map sub_dir back to doc_type
        doc_type = config.get("classifier", {}).get("subfolder_rules", {}).get(sub_dir)
        
        if not doc_type:
            return None
            
        # Try to parse vendor/model from device_slug
        parts = device_slug.split("_")
        vendor = parts[0].capitalize() if len(parts) > 0 else "Unknown"
        model = "_".join(parts[1:]).upper() if len(parts) > 1 else "Unknown"
        
        return {
            "doc_type": doc_type,
            "category_slug": f"{category_slug}/{group_slug}",
            "vendor": vendor,
            "model": model,
            "confidence": 1.0,
            "summary": f"Đặt thủ công tại /{sub_dir}",
            "device_slug": device_slug  # Keep consistency
        }
    except Exception:
        return None


async def process_new_file(
    file_path: str,
    config: dict,
    classifier: MedicalClassifier,
    store: IndexStore,
    wiki: WikiGenerator,
    taxonomy: Taxonomy,
):
    """
    Orchestrates the processing of a new document.
    """
    logger.info(f"--- Bắt đầu xử lý: {Path(file_path).name} ---")

    # 0. Kiểm tra nếu file đã có trong DB ở đường dẫn hiện tại thì bỏ qua (chống loop của watcher)
    existing = await store.get_file(file_path)
    if existing:
        logger.info(f"File đã tồn tại trong DB, bỏ qua: {file_path}")
        return

    # 1. Phân loại
    classification = None
    manual_info = detect_manual_placement(file_path, config)
    
    if manual_info:
        logger.info(f"Phát hiện file đặt thủ công: {manual_info.get('device_slug')}")
        classification = manual_info
    else:
        try:
            classification = await classifier.classify_file(file_path)
            logger.info(f"Kết quả phân loại AI: {json.dumps(classification, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"Dừng tiến trình do lỗi phân loại AI: {e}")
            # ... handle error as before ...
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            group_chat_id = config["services"]["telegram"].get("group_chat_id")
            if token and group_chat_id:
                try:
                    bot = Bot(token=token)
                    safe_filename = html.escape(Path(file_path).name)
                    safe_error = html.escape(str(e))
                    error_report = (
                        f"❌ <b>Lỗi phân loại tài liệu!</b>\n\n"
                        f"<b>File:</b> <code>{safe_filename}</code>\n"
                        f"<b>Lỗi:</b> {safe_error}\n\n"
                        f"Vui lòng kiểm tra lại quota hoặc thử lại sau."
                    )
                    await bot.send_message(
                        chat_id=group_chat_id, text=error_report, parse_mode=ParseMode.HTML
                    )
                except Exception as tg_err:
                    logger.error(f"Lỗi gửi Telegram báo lỗi: {tg_err}")
            return

    # Extract classified data
    doc_type = classification.get("doc_type", "khac")
    vendor = classification.get("vendor", "Unknown")
    model = classification.get("model", "Unknown")
    summary = classification.get("summary", "")
    confidence = classification.get("confidence", None)

    # Tự ước tính confidence nếu AI không trả về
    if confidence is None:
        if vendor != "Unknown" and model != "Unknown" and doc_type != "khac":
            confidence = 0.8  # Đủ thông tin: vendor + model + doc_type
        elif doc_type != "khac" and classification.get("category_slug"):
            confidence = 0.75  # Có doc_type và category là đủ
        else:
            confidence = 0.5   # Thông tin mơ hồ, để user xác nhận
        logger.info(f"AI không trả về confidence, ước tính: {confidence}")

    # Đảm bảo confidence là số hợp lệ
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5

    # Mapping doc_type sang tiếng Việt
    doc_type_vi = DOC_TYPE_MAP.get(doc_type, doc_type)

    # 2. Tạo slugs
    device_slug = build_device_slug(vendor, model)
    full_category_slug = classification.get("category_slug", "")

    if "/" in full_category_slug:
        parts = full_category_slug.split("/")
        category_slug = clean_name(parts[0])
        group_slug = clean_name(parts[1])
    else:
        category_slug = clean_name(full_category_slug) if full_category_slug else "chua_phan_loai"
        group_slug = "khac"

    category_slug = _CATEGORY_MAP.get(category_slug, category_slug)
    group_slug = _GROUP_MAP.get(group_slug, group_slug)

    # --- Strict Taxonomy Validation ---
    if not taxonomy.get_category(category_slug):
        logger.warning(f"AI sinh category_slug ảo '{category_slug}', fallback về 'chua_phan_loai'.")
        category_slug = "chua_phan_loai"
        group_slug = "khac"
    elif not taxonomy.get_group(category_slug, group_slug):
        logger.warning(
            f"AI sinh group_slug ảo '{group_slug}' (thuộc {category_slug}), fallback về 'khac'."
        )
        group_slug = "khac"

    # --- Always require manual confirmation as per SPECS (UC1) ---
    threshold = config.get("classifier", {}).get("confidence_threshold", 0.7)
    is_confident = confidence >= threshold

    # 3. Tính toán vị trí tương lai (nhưng CHƯA di chuyển)
    root = Path(os.path.expandvars(os.path.expanduser(config["paths"]["medical_devices_root"])))
    target_relative = Path(category_slug) / group_slug / device_slug

    if not is_confident:
        logger.info(f"Độ tin cậy thấp ({confidence} < {threshold}).")

    logger.info(f"Chờ người dùng xác nhận thủ công cho file: {file_path}")

    # 4. Lưu vào Database (Strict Integrity)
    try:
        sha256 = compute_sha256(file_path)
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng: Không thể tính sha256 cho {file_path}. Hủy xử lý. {e}")
        raise  # Strict integrity

    try:
        size_bytes = os.path.getsize(file_path)
    except OSError:
        size_bytes = 0

    file_id = await store.upsert_file(
        path=file_path,
        sha256=sha256,
        doc_type=doc_type,
        device_slug=device_slug,
        category_slug=category_slug,
        group_slug=group_slug,
        vendor=vendor,
        model=model,
        summary=summary,
        size_bytes=size_bytes,
        confirmed=False,  # ALWAYS False until user clicks approve
    )
    logger.info(f"Đã lưu vào DB (DRAFT): {file_path} (ID: {file_id})")

    # 5. Cập nhật Wiki -> Bỏ qua, chỉ làm khi user ấn Confirm

    file_info = {
        "id": file_id,
        "path": file_path,
        "vendor": vendor,
        "model": model,
        "doc_type": doc_type,
        "summary": summary,
        "category_slug": category_slug,
        "group_slug": group_slug,
        "device_slug": device_slug
    }
    
    report, reply_markup = render_draft_message(file_info, config, confidence, is_confident)

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    group_chat_id = config["services"]["telegram"].get("group_chat_id")

    if token and group_chat_id:
        try:
            bot = Bot(token=token)
            await bot.send_message(
                chat_id=group_chat_id,
                text=report,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            logger.info(f"Đã gửi báo cáo Telegram tới: {group_chat_id}")
        except Exception as e:
            logger.error(f"Lỗi gửi Telegram: {e}")

    logger.info("--- Xử lý hoàn tất ---")


async def main_cli():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    if len(sys.argv) < 2:
        print("Usage: python process_event.py <file_path>")
        return

    config_path = "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    classifier = MedicalClassifier(config_path)
    store = IndexStore(config["paths"]["db_file"])
    await store.init()
    wiki = WikiGenerator(config_path)
    taxonomy = Taxonomy(config["paths"]["taxonomy_file"])

    try:
        await process_new_file(sys.argv[1], config, classifier, store, wiki, taxonomy)
    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main_cli())
