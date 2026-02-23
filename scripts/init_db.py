import asyncio
import logging
from pathlib import Path

import yaml

from app.index_store import IndexStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    # Load config
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    db_path = config["paths"]["db_file"]
    logger.info(f"Khởi tạo database tại: {db_path}")

    store = IndexStore(db_path)
    await store.init()

    if Path(db_path).exists():
        logger.info("✅ Database đã được khởi tạo thành công.")
    else:
        logger.error("❌ Không thể tạo tệp database.")


if __name__ == "__main__":
    asyncio.run(init_db())
