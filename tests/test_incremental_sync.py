from __future__ import annotations

from pathlib import Path

from app.config import AppSettings
from indexing.sync_service import IndexSyncService
from storage.milvus_repo import MilvusRepo
from storage.sqlite_repo import SQLiteRepo
from indexing.embedder_openai import OpenAIEmbedder


def _make_service(tmp_path: Path) -> IndexSyncService:
    vault = tmp_path / "vault"
    vault.mkdir()
    settings = AppSettings(
        vault_path=vault,
        sqlite_path=tmp_path / "meta.db",
        embedding_api_key=None,
        embedding_dimensions=64,
    )
    sqlite_repo = SQLiteRepo(settings.sqlite_path)
    milvus_repo = MilvusRepo(str(tmp_path / "milvus.db"), "test_blocks", dims=64)
    embedder = OpenAIEmbedder(None, "text-embedding-3-small", 64, 32)
    return IndexSyncService(settings, sqlite_repo, milvus_repo, embedder)


def test_sync_add_modify_delete(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    note = service._settings.vault_path / "a.md"
    note.write_text("# A\nhello world", encoding="utf-8")
    first = service.sync()
    assert "a.md" in first["changes"]["added"]

    note.write_text("# A\nhello world changed", encoding="utf-8")
    second = service.sync()
    assert "a.md" in second["changes"]["modified"]

    note.unlink()
    third = service.sync()
    assert "a.md" in third["changes"]["deleted"]


def test_milvus_lite_backend_creates_local_db(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "milvus.db"
    repo = MilvusRepo(str(db_path), "test_blocks", dims=8)

    assert db_path.parent.exists()
    assert repo.backend() in {"milvus", "fallback-memory"}


def test_sync_skips_excluded_directory(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "public.md").write_text("# public\nhello", encoding="utf-8")
    private_dir = vault / "private"
    private_dir.mkdir()
    (private_dir / "secret.md").write_text("# secret\nworld", encoding="utf-8")

    settings = AppSettings(
        vault_path=vault,
        sqlite_path=tmp_path / "meta.db",
        embedding_api_key=None,
        embedding_dimensions=64,
        exclude_dirs=["private"],
    )
    sqlite_repo = SQLiteRepo(settings.sqlite_path)
    milvus_repo = MilvusRepo(str(tmp_path / "milvus.db"), "test_blocks", dims=64)
    embedder = OpenAIEmbedder(None, "text-embedding-3-small", 64, 32)
    service = IndexSyncService(settings, sqlite_repo, milvus_repo, embedder)

    result = service.sync()

    assert result["changes"]["added"] == ["public.md"]
    assert sqlite_repo.get_note("public.md") is not None
    assert sqlite_repo.get_note("private/secret.md") is None
