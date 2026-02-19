import asyncio
import logging
import os
import aiosqlite
import yaml
from app.index_store import IndexStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_db():
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    store = IndexStore(config["paths"]["db_file"])
    await store.init()
    
    logger.info("Đang quét Database để tìm file rác...")
    
    deleted_count = 0
    
    async with aiosqlite.connect(store._db_path) as db:
        db.row_factory = aiosqlite.Row
        # Lấy danh sách ID và Path
        async with db.execute("SELECT id, path FROM files") as cursor:
            rows = await cursor.fetchall()
            
        # Duyệt qua từng file, kiểm tra tồn tại trên đĩa
        for row in rows:
            file_path = row["path"]
            file_id = row["id"]
            
            if not os.path.exists(file_path):
                logger.warning(f"File không tồn tại: {file_path} (ID: {file_id}) -> XOÁ")
                await db.execute("DELETE FROM files WHERE id = ?", (file_id,))
                deleted_count += 1
        
        await db.commit()
        
    logger.info(f"--- Hoàn tất ---")
    logger.info(f"Đã xóa {deleted_count} bản ghi rác.")

if __name__ == "__main__":
    asyncio.run(cleanup_db())
