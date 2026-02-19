import asyncio
import logging
from app.wiki_generator import WikiGenerator
from app.taxonomy import Taxonomy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_wiki_index():
    # Load Taxonomy
    taxonomy = Taxonomy("data/taxonomy.yaml")
    
    # Init Generator
    gen = WikiGenerator("config.yaml")
    
    # Generate Indexes
    logger.info("Đang sinh các tệp Index cho Wiki...")
    paths = gen.generate_indexes(taxonomy)
    
    for p in paths:
        if p.exists():
            logger.info(f"✅ Đã tạo: {p}")
        else:
            logger.error(f"❌ Lỗi: Không thấy file {p}")

if __name__ == "__main__":
    asyncio.run(test_wiki_index())
