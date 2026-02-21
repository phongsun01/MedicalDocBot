import os
import shutil
import yaml
from pathlib import Path

def reset_env():
    print("🧨 Đang dọn dẹp môi trường để kiểm thử lại từ đầu...")
    
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    # 1. Xóa Database
    db_file = Path(config["paths"]["db_file"])
    if db_file.exists():
        db_file.unlink()
        print(f"✅ Đã xóa Database SQLite tại: {db_file}")
    
    # 2. Dọn dẹp thư mục MedicalDevices
    medical_devices_root = Path(os.path.expandvars(os.path.expanduser(config["paths"]["medical_devices_root"])))
    
    # Giữ lại các thư mục hệ thống / cache
    whitelist = {".obsidian", ".backup", ".cache", "extracted", "logs", ".git"}
    
    if medical_devices_root.exists():
        deleted_count = 0
        for item in medical_devices_root.iterdir():
            if item.name in whitelist:
                continue
                
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                deleted_count += 1
                print(f"🗑️ Đã xóa: {item.name}")
            except Exception as e:
                print(f"❌ Lỗi khi xóa {item.name}: {e}")
                
        print(f"✅ Đã dọn dẹp {deleted_count} file/thư mục trong {medical_devices_root}.")
                
    print("\n🎉 HOÀN TẤT RESET! Môi trường đã sạch sẽ 100%. Mời bạn kéo thả file vào lại để test.")

if __name__ == "__main__":
    reset_env()
