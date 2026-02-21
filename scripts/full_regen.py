import asyncio
import os
import shutil
from pathlib import Path
import yaml

from app.index_store import IndexStore
from app.taxonomy import Taxonomy
from app.wiki_generator import WikiGenerator

# Bản đồ dọn dẹp các slug rác (do AI hallucinate) về Taxonomy chuẩn
CATEGORY_MAP = {
    "Unknown":       "chua_phan_loai",
    "khac":          "chua_phan_loai",
    "ngoai_khoa":    "thiet_bi_phong_mo",
    "phau_thuat":    "thiet_bi_phong_mo",
    "phong_mo":      "thiet_bi_phong_mo",
    "thiet-bi-phong-mo": "thiet_bi_phong_mo",
    "thiet_bi_hoi_suc":  "hoi_suc_cap_cuu",
    "thiet_bi_hoi_suc_gay_me": "gay_me_may_tho",
}

GROUP_MAP = {
    "Unknown":                "khac",
    "may_tho":                "may_tho_hoi_suc",
    "phong_mo":               "khac",
    "thiet_bi_phong_mo":      "khac",
    "ban-mo":                 "ban_mo",
    "monitor_benh_nhan":      "monitor",
    "may_theo_doi_benh_nhan": "monitor",
}

async def fix_and_regen():
    print("🚀 Bắt đầu dọn dẹp Database và Sinh lại Wiki...")
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    store = IndexStore(config["paths"]["db_file"])
    await store.init()
    
    # 1. Update Database
    print("1. Đang fix các category_slug mồ côi trong DB...")
    async with store._conn.execute("SELECT id, category_slug, group_slug FROM files") as cursor:
        rows = await cursor.fetchall()
        
    updated = 0
    for row in rows:
        fid, cslug, gslug = row
        new_cslug = CATEGORY_MAP.get(cslug, cslug)
        new_gslug = GROUP_MAP.get(gslug, gslug)
        if new_cslug != cslug or new_gslug != gslug:
            await store._conn.execute(
                "UPDATE files SET category_slug = ?, group_slug = ? WHERE id = ?",
                (new_cslug, new_gslug, fid)
            )
            updated += 1
            
    await store._conn.commit()
    print(f"✅ Đã dọn dẹp {updated} bản ghi trong DB!")

    # 2. Xóa sạch thư mục Wiki cũ để dọn rác
    wiki_dir = Path(os.path.expandvars(os.path.expanduser(config["paths"]["wiki_dir"])))
    print(f"2. Xóa thư mục Wiki cũ: {wiki_dir}...")
    if wiki_dir.exists():
        shutil.rmtree(wiki_dir)
    wiki_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Chạy lại Wiki Generator
    print("3. Đang render lại toàn bộ Markdown...")
    taxonomy = Taxonomy(config["paths"]["taxonomy_file"])
    wiki = WikiGenerator(config_path)
    
    # Render các file thiết bị
    devices = await store.search(limit=10000)
    # Gom nhóm theo thiết bị
    dev_map = {}
    for f in devices:
        slug = f["device_slug"]
        if slug not in dev_map:
            dev_map[slug] = []
        dev_map[slug].append(f)
        
    for slug, flist in dev_map.items():
        sample = flist[0]
        device_info = {
            "vendor": sample.get("vendor", ""),
            "model": sample.get("model", ""),
            "category_id": sample.get("category_slug", ""),
            "category_slug": f"{sample.get('category_slug')}/{sample.get('group_slug')}",
        }
        wiki.update_device_wiki(slug, device_info, flist, taxonomy=taxonomy)
        
    # Chạy index tổng cuối cùng một lần nữa để chắc chắn
    wiki.generate_indexes(taxonomy)
    await store.close()
    print("🎉 Hoàn tất!")

if __name__ == "__main__":
    asyncio.run(fix_and_regen())
