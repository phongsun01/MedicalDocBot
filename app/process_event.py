import asyncio
import logging
import sys
import json
from pathlib import Path
from app.classifier import MedicalClassifier
from app.index_store import IndexStore
from app.wiki_generator import WikiGenerator
from app.slug import build_device_slug
from app.taxonomy import Taxonomy
import yaml
import os
import shutil
import re
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def clean_name(s: str) -> str:
    """Sanitize filename (giữ lại tiếng Việt, thay ký tự đặc biệt bằng _)."""
    s = s.replace("/", "_").replace("\\", "_")
    return re.sub(r'[<>:"|?*]', '', s).strip()

async def process_new_file(file_path: str):
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 1. Khởi tạo các thành phần
    classifier = MedicalClassifier(config_path)
    store = IndexStore(config["paths"]["db_file"])
    wiki = WikiGenerator(config_path)
    taxonomy = Taxonomy(config["paths"]["taxonomy_file"])
    
    await store.init()
    
    # 2. Phân loại bằng Gemini
    logger.info(f"--- Bắt đầu xử lý: {Path(file_path).name} ---")
    classification = await classifier.classify_file(file_path)
    logger.info(f"Kết quả phân loại: {json.dumps(classification, ensure_ascii=False)}")
    
    doc_type = classification.get("doc_type", "khac")
    vendor = classification.get("vendor", "Unknown")
    model = classification.get("model", "Unknown")
    summary = classification.get("summary", "")
    
    # Mapping doc_type sang tiếng Việt
    doc_type_vi = DOC_TYPE_MAP.get(doc_type, doc_type)
    
    # 3. Tạo slugs
    device_slug = build_device_slug(vendor, model)
    # Lấy category từ taxonomy dựa trên classification (Azurion -> Tim mạch can thiệp)
    category_slug = "tim_mach_can_thiep"
    group_slug = "he_thong_can_thiep"
    
    # 3b. Di chuyển file vào thư mục phân loại
    # Lấy nhãn tiếng Việt để tạo thư mục (giống Wiki)
    cat_data = taxonomy.get_category(category_slug)
    cat_label = cat_data["label_vi"] if cat_data else category_slug
    
    group_data = taxonomy.get_group(category_slug, group_slug)
    group_label = group_data["label_vi"] if group_data else group_slug
    
    # Xây dựng đường dẫn đích
    root = Path(os.path.expandvars(os.path.expanduser(config["paths"]["medical_devices_root"])))
    target_relative = Path(clean_name(cat_label)) / clean_name(group_label)
    target_dir = root / target_relative
    target_dir.mkdir(parents=True, exist_ok=True)
    
    new_path = target_dir / Path(file_path).name
    
    # Chỉ di chuyển nếu file chưa ở đúng chỗ
    moved = False
    if Path(file_path).resolve() != new_path.resolve():
        try:
            shutil.move(file_path, new_path)
            logger.info(f"Đã di chuyển file đến: {new_path}")
            # Xóa entry cũ trong DB nếu tồn tại (để tránh double)
            await store.delete_file(str(file_path)) 
            file_path = str(new_path) # Cập nhật file_path để lưu vào DB
            moved = True
        except Exception as e:
            logger.error(f"Lỗi khi di chuyển file: {e}")
    else:
        logger.info("File đã ở đúng thư mục phân loại.")
            
    # 4. Lưu vào Database
    sha256 = "dummy_sha256" # Sẽ dùng compute_sha256 trong prod
    from app.index_store import compute_sha256
    try:
        sha256 = compute_sha256(file_path)
    except:
        pass
    # Lấy kích thước file mới từ path đã di chuyển
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
    logger.info(f"Đã lưu vào DB với ID: {file_path}")
    
    # 5. Cập nhật Wiki
    device_info = {
        "vendor": vendor,
        "model": model,
        "category_id": category_slug,
        "category_slug": f"{category_slug}/{group_slug}"
    }
    
    # Lấy tất cả file của device này để render wiki
    all_files = await store.search(device_slug=device_slug)
    wiki_path = wiki.update_device_wiki(device_slug, device_info, all_files, taxonomy=taxonomy)
    logger.info(f"Wiki đã được cập nhật: {wiki_path}")
    
    # 6. Gửi báo cáo Telegram qua OpenClaw
    location_msg = f"\n📁 **Đã lưu vào:** `{target_relative}`" if moved else ""
    
    report = f"📄 **Phát hiện tài liệu mới!**\n\n" \
             f"**File:** `{Path(file_path).name}`\n" \
             f"**Hãng:** {vendor}\n" \
             f"**Model:** {model}\n" \
             f"**Loại:** {doc_type_vi}\n" \
             f"**Tóm tắt:** {summary}\n" \
             f"{location_msg}\n\n" \
             f"✅ Đã cập nhật Wiki & Database."
    
    # Gửi tin nhắn qua Telegram Bot API (Direct)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    group_chat_id = config["services"]["telegram"].get("group_chat_id")
    
    if token and group_chat_id:
        try:
            bot = Bot(token=token)
            # escape special markdown chars if needed, but for now trust report format or use MarkdownV2
            # Report đang dùng markdown legacy (**bold**, `code`), phù hợp với ParseMode.MARKDOWN
            await bot.send_message(chat_id=group_chat_id, text=report, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Đã gửi báo cáo Telegram tới: {group_chat_id}")
        except Exception as e:
            logger.error(f"Lỗi gửi Telegram: {e}")
    else:
        logger.warning("Không tìm thấy TELEGRAM_BOT_TOKEN hoặc group_chat_id, bỏ qua gửi tin.")
    
    logger.info("--- Xử lý hoàn tất ---")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_event.py <file_path>")
    else:
        asyncio.run(process_new_file(sys.argv[1]))
