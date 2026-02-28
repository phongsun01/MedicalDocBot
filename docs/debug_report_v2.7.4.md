# Báo cáo Debug — MedicalDocBot v2.7.4

Sau khi đọc toàn bộ source code (`app/`, `tests/`), CHANGELOG, và đối chiếu kỹ lưỡng, dưới đây là các lỗi còn tồn tại trong v2.7.4: [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/CHANGELOG.md)

***

## 🔴 LỖI NGHIÊM TRỌNG (Runtime Error)

### BUG #1 — `process_event.py`: Sử dụng `ParseMode.HTML` mà không import
**File:** `app/process_event.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/process_event.py)

Trong hàm `process_new_file`, tại đoạn xử lý lỗi phân loại AI và tại đoạn gửi báo cáo draft, code gọi:
```python
parse_mode=ParseMode.HTML
```
Nhưng `ParseMode` **không được import** trong file. Các import hiện tại chỉ có:
```python
from telegram import Bot
from telegram.helpers import escape_markdown
```
`ParseMode` bị thiếu hoàn toàn. Khi hệ thống cố gắng gửi Telegram notification, sẽ xảy ra `NameError: name 'ParseMode' is not defined`.

**Sửa:** Thêm `from telegram.constants import ParseMode` vào phần import.

***

### BUG #2 — `process_event.py`: Import `escape_markdown` thừa nhưng vẫn còn
**File:** `app/process_event.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/process_event.py)

CHANGELOG v2.7.4 tuyên bố "Loại bỏ import thừa `escape_markdown`" (BUG #9), nhưng dòng: [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/process_event.py)
```python
from telegram.helpers import escape_markdown
```
**vẫn còn tồn tại** trong file. Import này không được sử dụng ở bất kỳ đâu trong file (toàn bộ code dùng `html.escape`). Đây là dead import gây hiểu lầm và cho thấy BUG #9 chưa thực sự được fix.

***

## 🟠 LỖI LOGIC / SAI HÀNH VI

### BUG #3 — `app/ui.py`: Dùng Markdown syntax bên trong HTML message
**File:** `app/ui.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/ui.py)

Hàm `render_draft_message` tạo HTML string but dùng `**bold**` Markdown:
```python
f"📄 **Phát hiện tài liệu mới!** (Độ tin cậy cao)\n\n"
f"**File:** `{safe_filename}`\n"
f"**Hãng:** {safe_vendor}\n"
...
f"**Tóm tắt:** _{safe_summary}_\n\n"
```
Tất cả các `**...**` và `_..._` là cú pháp **Markdown**, nhưng message này được gửi với `parse_mode=ParseMode.HTML`. Telegram sẽ không render chúng thành bold/italic — chúng hiển thị nguyên dấu sao `**` trên màn hình người dùng. Đây là lỗi BUG #1/#2 mà v2.7.4 tuyên bố đã sửa nhưng thực tế **chưa sửa trong `ui.py`**. [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/CHANGELOG.md)

**Sửa:** Thay `**text**` thành `<b>text</b>` và `_text_` thành `<i>text</i>`.

***

### BUG #4 — `app/telegram_bot.py`: `latest` và `find` dùng Markdown trong HTML
**File:** `app/telegram_bot.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/telegram_bot.py)

Tương tự, hàm `latest` xây dựng message:
```python
msg = "🆕 **5 Tài liệu mới nhất:**\n\n"
...
msg += f"{i}. **{name_safe}**\n"
msg += f"   📝 _{summary_safe}_\n\n"
```
Và hàm `find`:
```python
msg = f'🔎 **Kết quả cho "{keyword_safe}":**\n\n'
msg += f"{i}. **{name_safe}**\n"
```
Tất cả gọi `reply_html()` hoặc `reply_html(msg, ...)` nhưng chuỗi dùng `**Markdown**` thay vì `<b>HTML</b>`. CHANGELOG BUG #1, #2 tuyên bố đã sửa nhưng code vẫn còn sai. [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/CHANGELOG.md)

***

### BUG #5 — `tests/test_v272_fixes.py`: Test `test_send_file_to_user_html_escape` sẽ FAIL
**File:** `tests/test_v272_fixes.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/tests/test_v272_fixes.py)

Test assert:
```python
assert kwargs["caption"] == "📄 test_<12>&.pdf"
```
Nhưng hàm `_send_file_to_user` trong `telegram_bot.py` thực tế gửi:
```python
caption=f"📄 {_html.escape(Path(file_path).name)}"
```
`html.escape("test_<12>&.pdf")` → `"test_&lt;12&gt;&amp;.pdf"`, vậy caption thực tế là `"📄 test_&lt;12&gt;&amp;.pdf"`.

Nhưng test lại expect `"📄 test_<12>&.pdf"` (chưa escape). Test này **sẽ fail** vì giá trị kỳ vọng sai. CHANGELOG BUG #13 tuyên bố đã sửa test assert nhưng thực tế vẫn sai. [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/CHANGELOG.md)

***

### BUG #6 — `tests/test_index_store.py`: `upsert_file` signature không khớp
**File:** `tests/test_index_store.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/tests/test_v272_fixes.py)

Test gọi:
```python
row_id = await store.upsert_file(
    path="...", sha256="hash123", doc_type="tech",
    device_slug="ge_xr220", category_slug="imaging", size_bytes=1024,
)
```
Nhưng `IndexStore.upsert_file` hiện tại có các parameter mặc định đầy đủ — điều này **không gây lỗi**. Tuy nhiên trong `test_stats`, test gọi: [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/index_store.py)
```python
await store.upsert_file(path="/a.pdf", sha256="h1", doc_type="tech", device_slug="d1", category_slug="c1", size_bytes=100)
```
Đây là positional-style với keyword args — hoạt động đúng. **Không có bug thực sự** ở đây.

***

### BUG #7 — `app/index_store.py`: Import `ParseMode` không cần thiết
**File:** `app/index_store.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/index_store.py)

Dòng đầu file có:
```python
from telegram.constants import ParseMode
```
Nhưng `ParseMode` **không được sử dụng ở bất kỳ đâu** trong `index_store.py`. Đây là dead import thừa, gây phụ thuộc không cần thiết vào thư viện `telegram` trong module database thuần túy.

***

### BUG #8 — `app/ui.py`: `DOC_TYPE_MAP` thiếu entry `"lien_ket"`
**File:** `app/ui.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/ui.py)

`DOC_TYPE_MAP` trong `ui.py` chỉ có 8 loại:
```python
DOC_TYPE_MAP = {
    "ky_thuat", "cau_hinh", "bao_gia", "trung_thau",
    "hop_dong", "so_sanh", "thong_tin", "khac"
}
```
Nhưng AI prompt trong `classifier.py` định nghĩa 9 loại bao gồm `"lien_ket"`: [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/classifier.py)
```
doc_type: [ky_thuat, cau_hinh, bao_gia, trung_thau, hop_dong, so_sanh, thong_tin, lien_ket, khac]
```
Khi AI trả về `doc_type="lien_ket"`, hàm `DOC_TYPE_MAP.get(doc_type, "Khác")` sẽ fallback về `"Khác"` thay vì hiển thị tên tiếng Việt đúng. Đồng thời, `render_type_selection_menu` cũng không hiển thị loại `lien_ket` cho user chọn.

***

## 🟡 CẢNH BÁO / VẤN ĐỀ TIỀM ẨN

### BUG #9 — `app/index_store.py`: `update_file_metadata` không cập nhật `search_text`
**File:** `app/index_store.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/index_store.py)

Hàm `update_file_metadata` cho phép cập nhật `vendor`, `model`, `summary` nhưng **không tái tính toán lại `search_text`**. Sau khi user sửa vendor/model qua Telegram bot, cột `search_text` (dùng cho tìm kiếm không dấu) sẽ bị lỗi thời — tìm kiếm theo tên hãng/model mới sẽ không trả về kết quả đúng.

***

### BUG #10 — `test_v271_fixes.py`: `test_correction_values` phụ thuộc vào runtime import
**File:** `tests/test_v271_fixes.py` [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/tests/test_v271_fixes.py)

```python
def test_correction_values(self):
    from app.process_event import _CATEGORY_MAP, _GROUP_MAP
    assert _CATEGORY_MAP.get("ngoai_khoa") == "thiet_bi_phong_mo"
    assert _GROUP_MAP.get("Unknown") == "khac"
```
Import này sẽ kéo theo toàn bộ `process_event.py` — bao gồm `load_dotenv(override=False)` và nhiều import nặng khác. Nếu môi trường test thiếu `config.yaml` hoặc các dependency, test sẽ fail với `ImportError` hoặc `FileNotFoundError` thay vì báo lỗi rõ ràng.

***

## Tóm tắt

| # | File | Mức độ | Mô tả |
|---|------|--------|-------|
| 1 | `process_event.py` | 🔴 Critical | `ParseMode` không được import — `NameError` khi runtime |
| 2 | `process_event.py` | 🟠 Medium | `escape_markdown` import thừa, BUG #9 chưa thực sự fix |
| 3 | `ui.py` | 🟠 Medium | Dùng `**Markdown**` trong HTML message — không render đúng |
| 4 | `telegram_bot.py` | 🟠 Medium | `/latest`, `/find` dùng `**Markdown**` trong `reply_html()` |
| 5 | `tests/test_v272_fixes.py` | 🟠 Medium | Assert caption sai — test sẽ fail |
| 6 | `index_store.py` | 🟡 Low | Import `ParseMode` thừa trong module database |
| 7 | `ui.py` | 🟡 Low | `DOC_TYPE_MAP` thiếu `"lien_ket"` so với AI prompt |
| 8 | `index_store.py` | 🟡 Low | `update_file_metadata` không cập nhật `search_text` |
| 9 | `test_v271_fixes.py` | 🟡 Low | Import nặng trong test có thể gây lỗi môi trường |

**Lỗi nghiêm trọng nhất cần fix ngay là BUG #1**: thiếu `from telegram.constants import ParseMode` trong `process_event.py` sẽ làm crash toàn bộ luồng xử lý file mỗi khi cần gửi thông báo Telegram. [raw.githubusercontent](https://raw.githubusercontent.com/phongsun01/MedicalDocBot/main/app/process_event.py)
