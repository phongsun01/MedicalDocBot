import asyncio
import logging
import sys
import json
from pathlib import Path
from app.classifier import MedicalClassifier
from app.index_store import IndexStore
from app.wiki_generator import WikiGenerator
from app.slug import build_device_slug
import yaml
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_new_file(file_path: str):
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 1. Khởi tạo các thành phần
    classifier = MedicalClassifier(config_path)
    store = IndexStore(config["paths"]["db_file"])
    wiki = WikiGenerator(config_path)
    
    await store.init()
    
    # 2. Phân loại bằng Gemini
    logger.info(f"--- Bắt đầu xử lý: {Path(file_path).name} ---")
    classification = await classifier.classify_file(file_path)
    logger.info(f"Kết quả phân loại: {json.dumps(classification, ensure_ascii=False)}")
    
    doc_type = classification.get("doc_type", "khac")
    vendor = classification.get("vendor", "Unknown")
    model = classification.get("model", "Unknown")
    summary = classification.get("summary", "")
    
    # 3. Tạo slugs
    device_slug = build_device_slug(vendor, model)
    # Lấy category từ taxonomy dựa trên classification (tạm dùng doc_type hoặc category hint)
    category_slug = "tim_mach_can_thiep" # Giả định cho Azurion
    group_slug = "he_thong_can_thiep"
    
    # 4. Lưu vào Database
    sha256 = "dummy_sha256" # Sẽ dùng compute_sha256 trong prod
    from app.index_store import compute_sha256
    try:
        sha256 = compute_sha256(file_path)
    except:
        pass

    file_id = await store.upsert_file(
        path=file_path,
        sha256=sha256,
        doc_type=doc_type,
        device_slug=device_slug,
        category_slug=category_slug,
        group_slug=group_slug,
        confirmed=True
    )
    logger.info(f"Đã lưu vào DB với ID: {file_id}")
    
    # 5. Cập nhật Wiki
    device_info = {
        "vendor": vendor,
        "model": model,
        "category_id": category_slug,
        "category_slug": f"{category_slug}/{group_slug}"
    }
    
    # Lấy tất cả file của device này để render wiki
    all_files = await store.search(device_slug=device_slug)
    wiki_path = wiki.update_device_wiki(device_slug, device_info, all_files)
    logger.info(f"Wiki đã được cập nhật: {wiki_path}")
    
    # 6. Gửi báo cáo Telegram qua OpenClaw
    report = f"📄 **Phát hiện tài liệu mới!**\n\n" \
             f"**File:** `{Path(file_path).name}`\n" \
             f"**Hãng:** {vendor}\n" \
             f"**Model:** {model}\n" \
             f"**Loại:** {doc_type}\n" \
             f"**Tóm tắt:** {summary}\n\n" \
             f"✅ Đã cập nhật Wiki & Database."
    
    # Gọi OpenClaw CLI để gửi tin nhắn
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    target = "7504023077" # User ID đã pairing
    cmd = f"/opt/homebrew/opt/node@22/bin/node /opt/homebrew/lib/node_modules/openclaw/dist/index.js message send --channel telegram --target {target} --message '{report}'"
    os.system(cmd)
    
    logger.info("--- Xử lý hoàn tất ---")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_event.py <file_path>")
    else:
        asyncio.run(process_new_file(sys.argv[1]))
