import pytest

from app.index_store import IndexStore


@pytest.fixture
async def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    index_store = IndexStore(db_path)
    await index_store.init()
    yield index_store
    await index_store.close()


@pytest.mark.asyncio
async def test_upsert_and_fetch(store):
    # Test initial upsert
    row_id = await store.upsert_file(
        path="/path/to/device/manual.pdf",
        sha256="hash123",
        doc_type="tech",
        device_slug="ge_xr220",
        category_slug="imaging",
        size_bytes=1024,
    )
    assert row_id == 1

    # Test duplicate upsert (idempotency)
    row_id_2 = await store.upsert_file(
        path="/path/to/device/manual.pdf",
        sha256="hash123",
        doc_type="tech",
        device_slug="ge_xr220",
        category_slug="imaging",
        size_bytes=1024,
    )
    assert row_id == row_id_2

    # Test search
    results = await store.search(device_slug="ge_xr220")
    assert len(results) == 1
    assert results[0]["path"] == "/path/to/device/manual.pdf"


@pytest.mark.asyncio
async def test_stats(store):
    await store.upsert_file(path="/a.pdf", sha256="h1", doc_type="tech", device_slug="d1", category_slug="c1", size_bytes=100)
    await store.upsert_file(path="/b.pdf", sha256="h2", doc_type="price", device_slug="d2", category_slug="c1", size_bytes=200)

    stats = await store.stats()
    assert stats["total_files"] == 2
    assert stats["by_doc_type"]["tech"] == 1
    assert stats["by_doc_type"]["price"] == 1
    assert stats["by_category"]["c1"] == 2
