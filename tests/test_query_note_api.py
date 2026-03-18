from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_query_note_endpoint_returns_shape(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("# A\nalpha beta", encoding="utf-8")
    (vault / "b.md").write_text("# B\nalpha gamma", encoding="utf-8")

    monkeypatch.setenv("OBS_VAULT_PATH", str(vault))
    monkeypatch.setenv("OBS_SQLITE_PATH", str(tmp_path / "meta.db"))
    monkeypatch.setenv("OBS_EMBEDDING_DIMENSIONS", "64")
    monkeypatch.setenv("OBS_MILVUS_URI", str(tmp_path / "milvus.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/v1/index/rebuild")

    resp = client.post("/v1/query/note", json={"note_path": "a.md", "top_k": 5, "threshold": 0.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["note_path"] == "a.md"
    assert "blocks" in data
    assert "note_summary" in data


def test_search_endpoint_handles_invalid_fts_syntax(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("# A\nalpha beta", encoding="utf-8")
    (vault / "b.md").write_text("# B\nbeta gamma", encoding="utf-8")

    monkeypatch.setenv("OBS_VAULT_PATH", str(vault))
    monkeypatch.setenv("OBS_SQLITE_PATH", str(tmp_path / "meta.db"))
    monkeypatch.setenv("OBS_EMBEDDING_DIMENSIONS", "64")
    monkeypatch.setenv("OBS_MILVUS_URI", str(tmp_path / "milvus.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/v1/index/rebuild")

    # Unbalanced quote triggers sqlite FTS parser error without fallback handling.
    resp = client.post("/v1/query/search", json={"text": 'alpha "beta', "top_k": 5, "threshold": 0.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == 'alpha "beta'
    assert "matches" in data


def test_search_endpoint_relaxes_threshold_when_candidates_exist(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("# A\nalpha beta gamma delta", encoding="utf-8")
    (vault / "b.md").write_text("# B\ngamma theta", encoding="utf-8")

    monkeypatch.setenv("OBS_VAULT_PATH", str(vault))
    monkeypatch.setenv("OBS_SQLITE_PATH", str(tmp_path / "meta.db"))
    monkeypatch.setenv("OBS_EMBEDDING_DIMENSIONS", "64")
    monkeypatch.setenv("OBS_MILVUS_URI", str(tmp_path / "milvus.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/v1/index/rebuild")

    # A very high threshold should still return candidates after server-side relax fallback.
    resp = client.post("/v1/query/search", json={"text": "alpha", "top_k": 5, "threshold": 0.95})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "alpha"
    assert len(data["matches"]) >= 1


def test_clear_index_endpoint_removes_indexed_data(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("# A\nalpha beta", encoding="utf-8")
    (vault / "b.md").write_text("# B\nbeta gamma", encoding="utf-8")

    monkeypatch.setenv("OBS_VAULT_PATH", str(vault))
    monkeypatch.setenv("OBS_SQLITE_PATH", str(tmp_path / "meta.db"))
    monkeypatch.setenv("OBS_EMBEDDING_DIMENSIONS", "64")
    monkeypatch.setenv("OBS_MILVUS_URI", str(tmp_path / "milvus.db"))
    app = create_app()
    client = TestClient(app)
    client.post("/v1/index/rebuild")

    before = client.get("/v1/index/status")
    assert before.status_code == 200
    assert before.json()["note_count"] >= 1

    cleared = client.post("/v1/index/clear")
    assert cleared.status_code == 200
    assert cleared.json()["status"] == "success"

    after = client.get("/v1/index/status")
    assert after.status_code == 200
    assert after.json()["note_count"] == 0
    assert after.json()["block_count"] == 0
