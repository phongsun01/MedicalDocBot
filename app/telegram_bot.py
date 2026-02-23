"""
telegram_bot.py — Bot tương tác cho MedicalDocBot.

Chức năng:
- /start, /help: Hướng dẫn danh sách lệnh.
- /latest: Xem 5 tài liệu mới nhất.
- /find <keyword>: Tìm kiếm tài liệu theo tên, model, nội dung tóm tắt.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.index_store import IndexStore

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# State
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
    store: IndexStore | None = context.bot_data.get("store")
    if not store:
        await update.message.reply_text("❌ Lỗi: Database chưa kết nối.")
        return

    try:
        results = await store.search(limit=5, order_by="updated_at DESC")

        if not results:
            await update.message.reply_text("📭 Kho tài liệu hiện đang trống.")
            return

        msg = "🆕 <b>5 Tài liệu mới nhất:</b>\n\n"
        import html
        for i, row in enumerate(results, 1):
            name = Path(row["path"]).name
            doc_type = row.get("doc_type", "Chưa phân loại")
            vendor = row.get("vendor", "Unknown")
            summary = row.get("summary", "Không có tóm tắt")
            
            # Cắt ngắn summary nếu quá dài
            if len(summary) > 50:
                summary = summary[:47] + "..."
            
            name_safe = html.escape(name)
            vendor_safe = html.escape(str(vendor))
            summary_safe = html.escape(summary)
            
            msg += f"{i}. <b>{name_safe}</b>\n"
            msg += f"   🏷 {doc_type} | 🏭 {vendor_safe}\n"
            msg += f"   📝 <i>{summary_safe}</i>\n\n"

        await update.message.reply_html(msg)

    except Exception as e:
        logger.error(f"Lỗi lệnh /latest: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra khi truy vấn dữ liệu.")


async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tìm kiếm file theo từ khóa."""
    if not context.args:
        await update.message.reply_text(
            "💡 Cách dùng: <code>/find &lt;từ khóa&gt;</code>\nVí dụ: <code>/find philips</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    keyword = " ".join(context.args)
    store: IndexStore | None = context.bot_data.get("store")
    if not store:
        return

    await update.message.reply_text(f'🔍 Đang tìm kiếm: "{keyword}"...')

    try:
        from app.search import execute_smart_search

        results = await execute_smart_search(store, keyword, limit=5)

        if not results:
            await update.message.reply_text(f'❌ Không tìm thấy tài liệu nào khớp với "{keyword}".')
            return

        keyboard = []
        import html
        keyword_safe = html.escape(keyword)

        msg = f'🔎 <b>Kết quả cho "{keyword_safe}":</b>\n\n'
        for i, row in enumerate(results, 1):
            name = Path(row["path"]).name
            doc_type = row.get("doc_type", "Unknown")
            vendor = row.get("vendor", "Unknown")
            file_path_str = str(row["path"]).replace("/Users/xitrum/MedicalDevices/", "")
            file_id = row.get("id")

            name_safe = html.escape(name)
            doc_type_safe = html.escape(doc_type)
            vendor_safe = html.escape(str(vendor))
            file_path_safe = html.escape(file_path_str)

            msg += f"{i}. <b>{name_safe}</b>\n"
            msg += f"   🏷 {doc_type_safe} | 🏭 {vendor_safe}\n"
            msg += f"   📂 <code>{file_path_safe}</code>\n\n"

            # Thêm nút bấm tải file
            if file_id:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"📥 Tải file #{i} ({name[:20]}...)", callback_data=f"send_{file_id}"
                        )
                    ]
                )

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_html(msg, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Lỗi lệnh /find: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra khi tìm kiếm.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Báo cáo trạng thái hệ thống."""
    # (Giữ nguyên logic status cũ nhưng sửa lỗi nếu hàm bị lỗi)
    store: IndexStore | None = context.bot_data.get("store")
    if not store:
        await update.message.reply_text("🔴 Lỗi kết nối Database.", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        stats = await store.stats()
        count = stats.get("total_files", 0)
        # Sửa lỗi lấy config vì struct của config có thể khác
        model_name = (
            config.get("services", {}).get("9router", {}).get("model", "Unknown")
            if config
            else "Unknown"
        )

        import html
        msg = (
            f"🟢 <b>Hệ thống đang hoạt động</b>\n"
            f"- 🗂 Tổng số file: <code>{count}</code>\n"
            f"- 📡 Bot: Online\n"
            f"- 🧠 AI Model: <code>{html.escape(model_name)}</code>"
        )
    except Exception as e:
        msg = f"🔴 Lỗi lấy trạng thái: {e}"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def _send_file_to_user(bot, chat_id, store, file_id: int):
    """Logic cốt lõi gửi file."""
    if not store or not store.is_connected():
        await bot.send_message(chat_id=chat_id, text="❌ Lỗi: Database chưa kết nối.")
        return

    # Lấy thông tin file từ DB
    file_info = await store.get_file_by_id(file_id)

    if not file_info:
        await bot.send_message(
            chat_id=chat_id, text=f"❌ Không tìm thấy file có ID={file_id} trong máy chủ."
        )
        return

    file_path = str(file_info.get("path") or "")

    if not file_path or not os.path.exists(file_path):
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ File vật lý không còn tồn tại trên máy chủ:\n<code>{file_path}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    db_size = file_info.get("size_bytes")
    try:
        size_bytes = int(db_size) if db_size else os.path.getsize(file_path)
    except (ValueError, TypeError, OSError):
        size_bytes = 0

    # Giới hạn Telegram Bot là 50MB
    if size_bytes > 50 * 1024 * 1024:
        size_mb = size_bytes / (1024 * 1024)
        msg_err = (
            f"❌ <b>Tệp quá lớn ({size_mb:.1f} MB)!</b>\n\n"
            f"Telegram giới hạn bot chỉ gửi được tệp <50MB. Vui lòng truy cập thư mục trực tiếp:\n"
            f"📂 <code>{file_path}</code>"
        )
        await bot.send_message(chat_id=chat_id, text=msg_err, parse_mode=ParseMode.HTML)
        return

    # Gửi file
    msg = await bot.send_message(
        chat_id=chat_id,
        text=f"⏳ Đang tải tệp <b>{Path(file_path).name}</b>...",
        parse_mode=ParseMode.HTML,
    )
    try:
        with open(file_path, "rb") as doc:
            await bot.send_document(
                chat_id=chat_id, document=doc, caption=f"📄 {Path(file_path).name}"
            )
        await msg.delete()  # Xóa tin nhắn "Đang tải"
    except Exception as e:
        logger.error(f"Lỗi gửi file: {e}")
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg.message_id, text=f"❌ Có lỗi xảy ra khi tải file: {e}"
        )


async def send_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gửi file trực tiếp bằng lệnh /send <ID>"""
    if not context.args:
        await update.message.reply_text(
            "💡 Cách dùng: <code>/send &lt;ID_File&gt;</code>\nSử dụng /find để lấy ID hoặc bấm nút Tải file.",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        file_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID tệp phải là một số nguyên.")
        return

    store: IndexStore | None = context.bot_data.get("store")
    await _send_file_to_user(context.bot, update.effective_chat.id, store, file_id)


async def _safe_edit(query, text, parse_mode=None):
    try:
        await query.edit_message_text(text, parse_mode=parse_mode)
    except Exception as tg_err:
        if "Message is not modified" not in str(tg_err):
            logger.error(f"Lỗi khi edit_message_text: {tg_err}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý sự kiện click vào nút Inline Keyboard"""
    query = update.callback_query
    await query.answer()  # Báo cho Telegram biết là đã nhận được click

    data = query.data
    if not data:
        return

    store: IndexStore | None = context.bot_data.get("store")

    if data.startswith("send_"):
        try:
            file_id = int(data.split("_")[1])
            await _send_file_to_user(context.bot, update.effective_chat.id, store, file_id)
        except Exception as e:
            logger.error(f"Lỗi Callback send_: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="❌ Dữ liệu nút hỏng."
            )

    elif data.startswith("approve_"):
        try:
            file_id = int(data.split("_")[1])
            if not store:
                await query.edit_message_text("❌ Lỗi Database.")
                return

            file_info = await store.get_file_by_id(file_id)

            if not file_info:
                await query.edit_message_text("❌ Không tìm thấy file trong DB.")
                return

            file_path = file_info.get("path", "")

            # --- Thực hiện di chuyển file & Wiki ---
            import shutil
            from pathlib import Path

            from app.taxonomy import Taxonomy
            from app.wiki_generator import WikiGenerator

            # Lấy data
            category_slug = file_info.get("category_slug", "chua_phan_loai")
            group_slug = file_info.get("group_slug", "khac")
            device_slug = file_info.get("device_slug", "unknown")
            vendor = file_info.get("vendor", "Unknown")
            model = file_info.get("model", "Unknown")
            doc_type = file_info.get("doc_type", "khac")

            root = Path(
                os.path.expandvars(os.path.expanduser(config["paths"]["medical_devices_root"]))
            )
            target_relative = Path(category_slug) / group_slug / device_slug
            target_dir = root / target_relative
            target_dir.mkdir(parents=True, exist_ok=True)

            new_path = target_dir / Path(file_path).name

            if Path(file_path).resolve() != new_path.resolve() and os.path.exists(file_path):
                new_path_str = str(new_path)
                import unidecode

                search_data = f"{new_path_str} {vendor} {model} {file_info.get('summary', '')} {doc_type}".lower()
                search_text = unidecode.unidecode(search_data)

                try:
                    shutil.move(file_path, new_path)
                    await store.confirm_file_and_update_path(file_id, new_path_str, search_text)
                    file_path = new_path_str
                except Exception as move_err:
                    logger.error(f"Move file thất bại, rollback DB: {move_err}")
                    raise
            else:
                await store.confirm_file(file_id)

            # Cập nhật Wiki
            taxonomy = Taxonomy(config["paths"]["taxonomy_file"])
            wiki = WikiGenerator("config.yaml")

            device_info = {
                "vendor": vendor,
                "model": model,
                "category_id": category_slug,
                "category_slug": f"{category_slug}/{group_slug}",
            }
            all_files = await store.search(device_slug=device_slug)
            
            # Cập nhật file markdown riêng cho device
            wiki.update_device_wiki(device_slug, device_info, all_files, taxonomy=taxonomy)
            # Cập nhật lại toàn bộ các file Index.md (do có thư mục/device mới)
            wiki.generate_indexes(taxonomy)

            import html
            import datetime
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            msg = f"✅ Đã phê duyệt và xử lý xong ({now_str}):\n📁 <code>{html.escape(str(target_relative))}</code>"
            await _safe_edit(query, msg, parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Lỗi khi xử lý approve: {e}")
            await _safe_edit(query, f"❌ Có lỗi khi phê duyệt: {e}")

    elif data.startswith("edit_"):
        file_id = data.split("_")[1]
        msg = (
            f"Sắp tới mình sẽ hỗ trợ chọn loại tài liệu trực tiếp trên Telegram. "
            f"Tạm thời bạn có thể dùng lệnh /update {file_id} doc_type để sửa."
        )
        await query.message.reply_text(msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn văn bản (tự động tìm kiếm)."""
    # Chỉ auto-search trong private chat để tránh spam group
    if update.effective_chat.type != "private":
        return

    text = update.message.text
    if not text.startswith("/"):
        # Coi như là lệnh find
        # Need to pass the text as context.args for the find function
        context.args = text.split()
        await find(update, context)


async def main():
    global config

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

    # Lưu store vào bot_data để các handler sử dụng
    app.bot_data["store"] = store

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("send", send_file_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("healthcheck", status_command))  # Alias

    # Callback Handlers (Inline Keyboard)
    app.add_handler(CallbackQueryHandler(button_callback))

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
