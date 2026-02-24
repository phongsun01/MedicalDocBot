import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from app.index_store import IndexStore

@pytest.fixture
async def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    index_store = IndexStore(db_path)
    await index_store.init()
    yield index_store
    await index_store.close()

@pytest.mark.asyncio
async def test_update_file_metadata_allowlist(store):
    # Setup record
    file_id = await store.upsert_file("/test/path.pdf", "hash", "tech")
    
    # Valid update
    await store.update_file_metadata(file_id, {"vendor": "TestVendor", "model": "TestModel"})
    updated = await store.get_file_by_id(file_id)
    assert updated["vendor"] == "TestVendor"
    assert updated["model"] == "TestModel"
    
    # Invalid update
    with pytest.raises(ValueError):
        await store.update_file_metadata(file_id, {"invalid_column": "value"})

@pytest.mark.asyncio
async def test_send_file_to_user_html_escape(store):
    from app.telegram_bot import _send_file_to_user
    
    bot = Mock()
    bot.send_message = AsyncMock()
    bot.send_document = AsyncMock()
    
    # Upload test file with special characters
    special_name = "test_<12>&.pdf"
    file_id = await store.upsert_file(special_name, "hash", "tech")
    
    with open(special_name, "w") as f:
        f.write("content")
        
    await _send_file_to_user(bot, "chat_id", store, file_id)
    
    # Ensure call uses escaped caption
    bot.send_document.assert_called_once()
    kwargs = bot.send_document.call_args.kwargs
    assert kwargs["caption"] == "📄 test_&lt;12&gt;&amp;.pdf"
    
    os.remove(special_name)

@pytest.mark.asyncio
async def test_send_file_command_int_vs_string(store):
    from app.telegram_bot import send_file_command
    import app.telegram_bot as tb
    
    tb.config = {
        "services": {"telegram": {"group_chat_id": "123456", "admin_chat_id": 9999}}
    }
    
    update = Mock()
    update.effective_chat.id = 123456
    update.effective_user.id = 9999
    update.message.reply_text = AsyncMock()
    
    context = Mock()
    context.args = ["1"]
    context.bot_data = {"store": store}
    
    with patch("app.telegram_bot._send_file_to_user", new_callable=AsyncMock) as mocked_send:
        await send_file_command(update, context)
        mocked_send.assert_called_once()

@pytest.mark.asyncio
async def test_handle_message_clear_awaiting_input(store):
    from app.telegram_bot import handle_message
    
    update = Mock()
    update.message.text = "New Vendor"
    update.message.reply_to_message = Mock()
    update.message.reply_to_message.message_id = 42
    update.message.chat_id = "chat"
    
    context = Mock()
    context.user_data = {
        "awaiting_input": {
            "message_id": 42,
            "file_id": 999,  # Missing file ID
            "field": "vendor",
            "original_message_id": 11
        }
    }
    context.bot_data = {"store": store}
    
    # Expect failure to find file, but awaiting_input should still be cleared
    await handle_message(update, context)
    
    assert "awaiting_input" not in context.user_data
