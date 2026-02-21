import asyncio
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Tuple, Any

import yaml
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from app.classifier import MedicalClassifier
from app.index_store import IndexStore
from app.wiki_generator import WikiGenerator
from app.slug import build_device_slug
from app.taxonomy import Taxonomy
from app.utils import compute_sha256, clean_name

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions moved or removed (Dependency Injection used instead)

DOC_TYPE_MAP = {
    "ky_thuat": "Kỹ thuật",
    "cau_hinh": "Cấu hình",
    "bao_gia": "Báo giá",
    "trung_thau": "Trúng thầu",
    "hop_dong": "Hợp đồng",
    "so_sanh": "So sánh",
    "thong_tin": "Thông tin",
    "lien_ket": "Liên kết",
    "khac": "Khác"
}

# clean_name moved to app.utils

async def process_new_file(
    file_path: str,
    config: dict,
    classifier: MedicalClassifier,
    store: IndexStore,
    wiki: WikiGenerator,
    taxonomy: Taxonomy
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
        
    # 1. Phân loại bằng AI
    try:
        classification = await classifier.classify_file(file_path)
        logger.info(f"Kết quả phân loại: {json.dumps(classification, ensure_ascii=False)}")
        
        doc_type = classification.get("doc_type", "khac")
        vendor = classification.get("vendor", "Unknown")
        model = classification.get("model", "Unknown")
        summary = classification.get("summary", "")
        
    except Exception as e:
        logger.error(f"Dừng tiến trình do lỗi phân loại AI: {e}")
        
        # Báo lỗi lên Telegram (MarkdownV2)
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        group_chat_id = config["services"]["telegram"].get("group_chat_id")
        if token and group_chat_id:
            try:
                bot = Bot(token=token)
                safe_filename = escape_markdown(Path(file_path).name, version=2)
                safe_error = escape_markdown(str(e), version=2)
                error_report = f"❌ *Lỗi phân loại tài liệu\\!*\n\n" \
                               f"*File:* `{safe_filename}`\n" \
                               f"*Lỗi:* {safe_error}\n\n" \
                               f"Vui lòng kiểm tra lại quota hoặc thử lại sau\\."
                await bot.send_message(chat_id=group_chat_id, text=error_report, parse_mode=ParseMode.MARKDOWN_V2)
            except Exception as tg_err:
                logger.error(f"Lỗi gửi Telegram báo lỗi: {tg_err}")
                
        return
        
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

    # --- Auto-correct AI Hallucinations ---
    CATEGORY_MAP = {
        "ngoai_khoa": "thiet_bi_phong_mo",
        "phau_thuat": "thiet_bi_phong_mo",
        "phong_mo": "thiet_bi_phong_mo",
        "trang_thiet_bi_phong_mo": "thiet_bi_phong_mo",
        "thiet-bi-phong-mo": "thiet_bi_phong_mo",
        "thiet_bi_hoi_suc": "hoi_suc_cap_cuu",
        "thiet_bi_hoi_suc_gay_me": "gay_me_may_tho",
        "Unknown": "chua_phan_loai",
        "khac": "chua_phan_loai"
    }

    GROUP_MAP = {
        "Unknown": "khac",
        "may_tho": "may_tho_hoi_suc",
        "phong_mo": "khac",
        "thiet_bi_phong_mo": "khac",
        "ban-mo": "ban_mo",
        "monitor_benh_nhan": "monitor",
        "may_theo_doi_benh_nhan": "monitor",
        "bon_rua_tay_phau_thuat": "bon_rua_tay"
    }

    category_slug = CATEGORY_MAP.get(category_slug, category_slug)
    group_slug = GROUP_MAP.get(group_slug, group_slug)
    
    # --- Strict Taxonomy Validation ---
    if not taxonomy.get_category(category_slug):
        logger.warning(f"AI sinh category_slug ảo '{category_slug}', fallback về 'chua_phan_loai'.")
        category_slug = "chua_phan_loai"
        group_slug = "khac"
    elif not taxonomy.get_group(category_slug, group_slug):
        logger.warning(f"AI sinh group_slug ảo '{group_slug}' (thuộc {category_slug}), fallback về 'khac'.")
        group_slug = "khac"
    
    # 3. Di chuyển file vào thư mục phân loại
    root = Path(os.path.expandvars(os.path.expanduser(config["paths"]["medical_devices_root"])))
    target_relative = Path(category_slug) / group_slug / device_slug
    target_dir = root / target_relative
    target_dir.mkdir(parents=True, exist_ok=True)
    
    new_path = target_dir / Path(file_path).name
    
    # Chỉ di chuyển nếu file chưa ở đúng chỗ
    if Path(file_path).resolve() != new_path.resolve():
        try:
            # Xóa entry cũ trong DB trước nếu tồn tại (đề phòng move lỗi hoặc file ghi đè)
            await store.delete_file(str(file_path)) 
            shutil.move(file_path, new_path)
            logger.info(f"Đã di chuyển file đến: {new_path}")
            file_path = str(new_path)
        except Exception as e:
            logger.error(f"Lỗi khi di chuyển file: {e}")
            # Nếu move fail, ta vẫn tiếp tục với original path? Không, tốt nhất là dừng.
            return
            
    # 4. Lưu vào Database (Strict Integrity)
    try:
        sha256 = compute_sha256(file_path)
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng: Không thể tính sha256 cho {file_path}. Hủy xử lý. {e}")
        raise # Strict integrity
        
    try:
        size_bytes = os.path.getsize(file_path)
    except OSError:
        size_bytes = 0

    await store.upsert_file(
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
        confirmed=True
    )
    logger.info(f"Đã lưu vào DB: {file_path}")
    
    # 5. Cập nhật Wiki
    device_info = {
        "vendor": vendor,
        "model": model,
        "category_id": category_slug,
        "category_slug": f"{category_slug}/{group_slug}"
    }
    
    all_files = await store.search(device_slug=device_slug)
    wiki_path = wiki.update_device_wiki(device_slug, device_info, all_files, taxonomy=taxonomy)
    logger.info(f"Wiki đã được cập nhật: {wiki_path}")
    
    # 6. Gửi báo cáo Telegram (MarkdownV2)
    safe_vendor = escape_markdown(vendor, version=2)
    safe_model = escape_markdown(model, version=2)
    safe_doc_type = escape_markdown(doc_type_vi, version=2)
    safe_summary = escape_markdown(summary, version=2)
    safe_filename = escape_markdown(Path(file_path).name, version=2)
    safe_location = escape_markdown(str(target_relative), version=2)
    
    report = f"📄 *Phát hiện tài liệu mới\\!*\n\n" \
             f"*File:* `{safe_filename}`\n" \
             f"*Hãng:* {safe_vendor}\n" \
             f"*Model:* {safe_model}\n" \
             f"*Loại:* {safe_doc_type}\n" \
             f"*Tóm tắt:* {safe_summary}\n\n" \
             f"📁 *Đã lưu vào:* `{safe_location}`\n\n" \
             f"✅ Đã cập nhật Wiki & Database\\."
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    group_chat_id = config["services"]["telegram"].get("group_chat_id")
    
    if token and group_chat_id:
        try:
            bot = Bot(token=token)
            await bot.send_message(chat_id=group_chat_id, text=report, parse_mode=ParseMode.MARKDOWN_V2)
            logger.info(f"Đã gửi báo cáo Telegram tới: {group_chat_id}")
        except Exception as e:
            logger.error(f"Lỗi gửi Telegram: {e}")
    
    logger.info("--- Xử lý hoàn tất ---")

async def main_cli():
    if len(sys.argv) < 2:
        print("Usage: python process_event.py <file_path>")
        return
        
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
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
