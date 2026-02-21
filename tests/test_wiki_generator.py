import pytest
import os
import yaml
from app.wiki_generator import WikiGenerator
from app.taxonomy import Taxonomy

@pytest.fixture
def wiki_env(tmp_path):
    # Setup config
    config = {
        "paths": {
            "medical_devices_root": str(tmp_path / "MedicalDevices"),
            "wiki_dir": str(tmp_path / "MedicalDevices/wiki")
        },
        "wiki": {
            "template_dir": str(tmp_path / "templates"),
            "backup_before_write": True
        }
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
        
    # Setup folders
    os.makedirs(tmp_path / "MedicalDevices/wiki/devices", exist_ok=True)
    
    # Setup taxonomy
    tax_data = {
        "version": 2,
        "categories": {
            "imaging": {
                "label_vi": "Chẩn đoán hình ảnh",
                "sub": {"x_quang": "X-Quang"}
            }
        }
    }
    tax_path = tmp_path / "taxonomy.yaml"
    with open(tax_path, "w") as f:
        yaml.dump(tax_data, f)
        
    # Mock templates (simplified)
    os.makedirs(tmp_path / "templates", exist_ok=True)
    with open(tmp_path / "templates/model_template.md.j2", "w") as f:
        f.write("# {{device_info.model}}\n{% for dt, fs in file_groups.items() %}{% for f in fs %}- {{f.path}}{% endfor %}{% endfor %}")
    
    return {
        "config_path": str(config_path),
        "tax_path": str(tax_path),
        "templates_root": str(tmp_path / "templates")
    }

def test_wiki_index_generation(wiki_env):
    # We need to monkeypatch the template lookup to our tmp templates
    from jinja2 import Environment, FileSystemLoader
    
    gen = WikiGenerator(wiki_env["config_path"])
    # Manually override the jinja env to use our tmp templates
    gen._jinja = Environment(loader=FileSystemLoader(wiki_env["templates_root"]))
    
    t = Taxonomy(wiki_env["tax_path"])
    
    # In reality generate_indexes doesn't use j2 for indexes (it's hardcoded in the module)
    # Let's see if it runs without error
    gen.generate_indexes(t)
    
    assert os.path.exists(os.path.join(gen._wiki_dir, "00_Danh_muc_thiet_bi/00_Index.md"))
    assert os.path.exists(os.path.join(gen._wiki_dir, "Chẩn đoán hình ảnh/00_Index.md"))

def test_device_wiki_update(wiki_env):
    from jinja2 import Environment, FileSystemLoader
    gen = WikiGenerator(wiki_env["config_path"])
    gen._jinja = Environment(loader=FileSystemLoader(wiki_env["templates_root"]))
    
    device_slug = "ge_xr220"
    device_info = {"vendor": "GE", "model": "Optima XR220"}
    files = [{"path": "manual.pdf", "doc_type": "tech", "size_bytes": 100, "updated_at": "2026"}]
    
    wiki_path = gen.update_device_wiki(device_slug, device_info, files)
    assert os.path.exists(wiki_path)
    
    with open(wiki_path, "r") as f:
        content = f.read()
        assert "Optima XR220" in content
        assert "manual.pdf" in content
