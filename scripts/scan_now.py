import asyncio
import os
import sys
from pathlib import Path
from app.process_event import process_new_file
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scan_now")

async def scan_and_process(root_path: str):
    root = Path(os.path.expanduser(root_path))
    if not root.exists():
        logger.error(f"Root path not found: {root}")
        return

    logger.info(f"Scanning {root} for unclassified files...")
    
    # Chỉ quét file ở root folder (depth 0)
    for file_path in root.glob("*"):
        if file_path.is_file():
            if file_path.name.startswith("."): # ignore hidden
                continue
            if file_path.name in ["taxonomy.yaml", "config.yaml"]: # ignore config if any
                continue
                
            logger.info(f"👉 Found file: {file_path.name}")
            try:
                await process_new_file(str(file_path))
                logger.info(f"✅ Processed: {file_path.name}")
            except Exception as e:
                logger.error(f"❌ Failed to process {file_path.name}: {e}")

if __name__ == "__main__":
    root_dir = "~/MedicalDevices"
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    
    asyncio.run(scan_and_process(root_dir))
