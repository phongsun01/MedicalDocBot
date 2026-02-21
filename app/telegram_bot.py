"""
telegram_bot.py — Bot tương tác cho MedicalDocBot.

Chức năng:
- /start, /help: Hướng dẫn danh sách lệnh.
- /latest: Xem 5 tài liệu mới nhất.
- /find <keyword>: Tìm kiếm tài liệu theo tên, model, nội dung tóm tắt.
"""

import logging
import os
import yaml
import asyncio
from typing import Any
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from app.index_store import IndexStore

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

# Global store
store: IndexStore | None = None
config: dict[str, Any] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gửi tin nhắn chào mừng."""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Xin chào {user.mention_html()}!\n\n"
        "Tôi là <b>MedicalDocBot</b>. Tôi có thể giúp bạn tìm kiếm tài liệu thiết bị y tế.\n\n"
        "<b>Các lệnh hỗ trợ:</b>\n"
        "🔎 <code>/find &lt;từ khóa&gt;</code> - Tìm kiếm file (Model, Hãng, Tóm tắt)\n"
        "🆕 <code>/latest</code> - Xem 5 file mới nhất\n"
        "ℹ️ <code>/help</code> - Xem hướng dẫn này"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị hướng dẫn."""
    await start(update, context)

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lấy 5 file mới nhất."""
    if not store:
        await update.message.reply_text("❌ Lỗi: Database chưa kết nối.")
        return

    try:
        results = await store.search(limit=5, order_by="updated_at DESC")
        
        if not results:
            await update.message.reply_text("📭 Kho tài liệu hiện đang trống.")
            return

        msg = "🆕 <b>5 Tài liệu mới nhất:</b>\n\n"
        for idx, file in enumerate(results, 1):
            name = Path(file['path']).name
            doc_type = file.get('doc_type', 'Khác')
            vendor = file.get('vendor') or file.get('device_slug')
            summary = file.get('summary') or "Không có tóm tắt"
            
            # Cắt ngắn summary nếu quá dài
            if len(summary) > 50:
                summary = summary[:47] + "..."
            
            msg += f"{idx}. <b>{name}</b>\n"
            msg += f"   🏷 {doc_type} | 🏭 {vendor}\n"
            msg += f"   📝 <i>{summary}</i>\n\n"
            
        await update.message.reply_html(msg)
        
    except Exception as e:
        logger.error(f"Lỗi lệnh /latest: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra khi truy vấn dữ liệu.")

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tìm kiếm file theo từ khóa."""
    if not context.args:
        await update.message.reply_text("💡 Cách dùng: <code>/find &lt;từ khóa&gt;</code>\nVí dụ: <code>/find philips</code>", parse_mode=ParseMode.HTML)
        return

    keyword = " ".join(context.args)
    if not store:
        return

    await update.message.reply_text(f"🔍 Đang tìm kiếm: \"{keyword}\"...")

    try:
        results = await store.search(keyword=keyword, limit=5)
        
        if not results:
            await update.message.reply_text(f"❌ Không tìm thấy tài liệu nào khớp với \"{keyword}\".")
            return

        msg = f"🔎 <b>Kết quả cho \"{keyword}\":</b>\n\n"
        for idx, file in enumerate(results, 1):
            name = Path(file['path']).name
            file_path = file['path']
            doc_type = file.get('doc_type', 'Khác')
            vendor = file.get('vendor') or ""
            
            msg += f"{idx}. <b>{name}</b>\n"
            msg += f"   🏷 {doc_type} | {vendor}\n"
            msg += f"   📂 <code>{file_path}</code>\n\n"
            
        await update.message.reply_html(msg)

    except Exception as e:
        logger.error(f"Lỗi lệnh /find: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra khi tìm kiếm.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Báo cáo trạng thái hệ thống."""
    # Đếm số file trong DB
    try:
        count = await store.count_files()
        msg = (
            f"🟢 **Hệ thống đang hoạt động**\n"
            f"- 🗂 Tổng số file: `{count}`\n"
            f"- 📡 Bot: Online\n"
            f"- 🧠 AI Model: `{config['services']['gemini']['model']}`"
        )
    except Exception as e:
        msg = f"🔴 Lỗi kết nối Database: {e}"
        
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn văn bản (tự động tìm kiếm)."""
    text = update.message.text
    if not text.startswith('/'):
        # Coi như là lệnh find
        # Need to pass the text as context.args for the find function
        context.args = text.split()
        await find(update, context)

async def main():
    global config, store
    
    load_dotenv()
    
    # Load config
    config = load_config()
    
    # Init DB
    store = IndexStore(config["paths"]["db_file"])
    await store.init()
    
    # Init Bot
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ Thiếu TELEGRAM_BOT_TOKEN trong biến môi trường!")
        return

    app = ApplicationBuilder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("healthcheck", status_command)) # Alias
    
    # Message Handler (Non-command)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 MedicalDocBot Telegram đang chạy...")
    
    # Run lifecycle
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    try:
        # Chạy vô hạn cho đến khi bị stop
        stop_signal = asyncio.Future()
        await stop_signal
    except KeyboardInterrupt:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot đã dừng.")
