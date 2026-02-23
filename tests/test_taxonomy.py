import pytest
import yaml

from app.taxonomy import Taxonomy


@pytest.fixture
def taxonomy_file(tmp_path):
    data = {
        "version": 2,
        "categories": {
            "chan_doan_hinh_anh": {
                "label_vi": "Chẩn đoán hình ảnh",
                "label_en": "Imaging",
                "sub": {"x_quang": "X-Quang", "sieu_am": "Siêu âm"},
            }
        },
    }
    f = tmp_path / "taxonomy.yaml"
    with open(f, "w", encoding="utf-8") as fw:
        yaml.dump(data, fw, allow_unicode=True)
    return str(f)


def test_taxonomy_load(taxonomy_file):
    t = Taxonomy(taxonomy_file)
    assert t.category_count == 1
    slugs = [c["slug"] for c in t.list_categories()]
    assert "chan_doan_hinh_anh" in slugs


def test_taxonomy_lookup(taxonomy_file):
    t = Taxonomy(taxonomy_file)
    cat = t.get_category("chan_doan_hinh_anh")
    assert cat["label_vi"] == "Chẩn đoán hình ảnh"

    group = t.get_group("chan_doan_hinh_anh", "x_quang")
    assert group["label_vi"] == "X-Quang"


def test_taxonomy_invalid_lookup(taxonomy_file):
    t = Taxonomy(taxonomy_file)
    assert t.get_category("non_existent") is None
    assert t.get_group("chan_doan_hinh_anh", "non_existent") is None


def test_get_path_label(taxonomy_file):
    t = Taxonomy(taxonomy_file)
    label = t.get_path_label("chan_doan_hinh_anh", "x_quang")
    # Taxonomy.get_path_label uses the category label + group label
    assert label == "Chẩn đoán hình ảnh > X-Quang"
