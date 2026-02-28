import html
import os
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DOC_TYPE_MAP = {
    "ky_thuat": "Kỹ thuật",
    "cau_hinh": "Cấu hình",
    "bao_gia": "Báo giá",
    "trung_thau": "Trúng thầu",
    "hop_dong": "Hợp đồng",
    "so_sanh": "So sánh",
    "thong_tin": "Thông tin",
    "lien_ket": "Liên kết",
    "khac": "Khác",
}

def render_draft_message(file_info: dict, config: dict, confidence: float = None, is_confident: bool = True) -> tuple[str, InlineKeyboardMarkup]:
    """
    Renders the HTML message and the InlineKeyboardMarkup for a draft document.
    """
    esc = html.escape
    file_path = file_info.get("path", "")
    safe_filename = esc(Path(file_path).name)
    safe_vendor = esc(file_info.get("vendor", "Unknown"))
    safe_model = esc(file_info.get("model", "Unknown"))
    
    doc_type = file_info.get("doc_type", "khac")
    doc_type_vi = DOC_TYPE_MAP.get(doc_type, "Khác")
    safe_doc_type = esc(doc_type_vi)
    
    safe_summary = esc(file_info.get("summary", ""))
    
    category_slug = file_info.get("category_slug", "chua_phan_loai")
    group_slug = file_info.get("group_slug", "khac")
    device_slug = file_info.get("device_slug", "unknown")
    
    target_relative = Path(category_slug) / group_slug / device_slug
    safe_location = esc(str(target_relative))
    
    safe_confidence = f" ({confidence * 100:.0f}%)" if confidence is not None else ""

    if is_confident:
        report = (
            f"📄 <b>Phát hiện tài liệu mới!</b> (Độ tin cậy cao)\n\n"
            f"<b>File:</b> <code>{safe_filename}</code>\n"
            f"<b>Hãng:</b> {safe_vendor}\n"
            f"<b>Model:</b> {safe_model}\n"
            f"<b>Loại:</b> {safe_doc_type}{safe_confidence}\n"
            f"<b>Tóm tắt:</b> <i>{safe_summary}</i>\n\n"
            f"📁 <b>Đề xuất lưu vào:</b> <code>{safe_location}</code>\n\n"
            f"Vui lòng xác nhận để hệ thống lưu và cập nhật Wiki."
        )
    else:
        report = (
            f"⚠️ <b>Cần xác nhận phân loại!</b> (AI không chắc chắn)\n\n"
            f"<b>File:</b> <code>{safe_filename}</code>\n"
            f"<b>Hãng:</b> {safe_vendor}\n"
            f"<b>Model:</b> {safe_model}\n"
            f"<b>Loại:</b> {safe_doc_type}{safe_confidence}\n"
            f"<b>Tóm tắt:</b> <i>{safe_summary}</i>\n\n"
            f"📁 <b>Đề xuất lưu vào:</b> <code>{safe_location}</code>\n\n"
            f"Vui lòng xác nhận hoặc chỉnh sửa thông tin."
        )

    file_id = file_info.get("id")
    keyboard = [
        [
            InlineKeyboardButton("✅ Phê duyệt", callback_data=f"approve_{file_id}"),
            InlineKeyboardButton("✏️ Chỉnh sửa", callback_data=f"edit_menu_{file_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return report, reply_markup

def render_edit_menu(file_id: int) -> InlineKeyboardMarkup:
    """Renders the top-level edit menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🏭 Sửa Hãng", callback_data=f"edit_vendor_{file_id}")],
        [InlineKeyboardButton("💻 Sửa Model", callback_data=f"edit_model_{file_id}")],
        [InlineKeyboardButton("🏷 Sửa Loại", callback_data=f"edit_type_{file_id}")],
        [InlineKeyboardButton("↩️ Quay lại", callback_data=f"refresh_draft_{file_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def render_type_selection_menu(file_id: int) -> InlineKeyboardMarkup:
    """Renders a keyboard to select the document type."""
    keyboard = []
    row = []
    # Build 2-column grid of types
    for key, name in DOC_TYPE_MAP.items():
        row.append(InlineKeyboardButton(name, callback_data=f"set_type_{file_id}_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("↩️ Hủy", callback_data=f"edit_menu_{file_id}")])
    return InlineKeyboardMarkup(keyboard)
