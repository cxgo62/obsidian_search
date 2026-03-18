from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except Exception:  # pragma: no cover - optional runtime dependency
    Collection = None  # type: ignore[assignment]
    CollectionSchema = None  # type: ignore[assignment]
    DataType = None  # type: ignore[assignment]
    FieldSchema = None  # type: ignore[assignment]
    connections = None  # type: ignore[assignment]
    utility = None  # type: ignore[assignment]


class MilvusRepo:
    """
    Milvus adapter with in-memory fallback for local tests.
    """

    def __init__(self, uri: str, collection_name: str, dims: int = 1536) -> None:
        self._uri = uri
        self._collection_name = collection_name
        self._dims = dims
        self._fallback_store: dict[str, tuple[list[float], dict[str, Any]]] = {}
        self._collection = None
        if connections is None:
            return
        try:
            self._prepare_local_uri(uri)
            connections.connect(alias="default", uri=uri)
            self._collection = self._ensure_collection(collection_name, dims)
        except Exception:
            self._collection = None

    def _prepare_local_uri(self, uri: str) -> None:
        if uri.startswith(("http://", "https://", "tcp://", "grpc://", "unix:")):
            return
        if uri.endswith(".db"):
            Path(uri).parent.mkdir(parents=True, exist_ok=True)

    def backend(self) -> str:
        if self._collection is not None:
            return "milvus"
        return "fallback-memory"

    def _ensure_collection(self, name: str, dims: int):
        assert utility is not None and FieldSchema is not None and CollectionSchema is not None and DataType is not None
        if not utility.has_collection(name):
            schema = CollectionSchema(
                fields=[
                    FieldSchema("block_uid", DataType.VARCHAR, is_primary=True, auto_id=False, max_length=256),
                    FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=dims),
                    FieldSchema("note_path", DataType.VARCHAR, max_length=512),
                ],
                description="Obsidian block vectors",
            )
            c = Collection(name=name, schema=schema)
            c.create_index("embedding", self._index_params())
            c.load()
            return c
        c = Collection(name)
        c.load()
        return c

    def _index_params(self) -> dict[str, Any]:
        if self._uri.endswith(".db"):
            return {"index_type": "AUTOINDEX", "metric_type": "COSINE", "params": {}}
        return {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}

    def upsert(self, rows: Iterable[dict[str, Any]]) -> None:
        rows = list(rows)
        if self._collection is None:
            for r in rows:
                self._fallback_store[r["block_uid"]] = (r["embedding"], {"note_path": r.get("note_path", "")})
            return
        if not rows:
            return
        block_uids = [r["block_uid"] for r in rows]
        embeddings = [r["embedding"] for r in rows]
        note_paths = [r.get("note_path", "") for r in rows]
        quoted = ",".join([f'"{u}"' for u in block_uids])
        self._collection.delete(f"block_uid in [{quoted}]")
        self._collection.insert([block_uids, embeddings, note_paths])
        self._collection.flush()

    def delete(self, block_uids: Iterable[str]) -> None:
        uids = list(block_uids)
        if not uids:
            return
        if self._collection is None:
            for uid in uids:
                self._fallback_store.pop(uid, None)
            return
        quoted = ",".join([f'"{u}"' for u in uids])
        self._collection.delete(f"block_uid in [{quoted}]")

    def clear(self) -> None:
        if self._collection is None:
            self._fallback_store.clear()
            return
        self._collection.delete('block_uid != ""')
        self._collection.flush()

    def search(self, query_vector: list[float], top_k: int, exclude_note: str | None = None) -> list[dict[str, Any]]:
        if self._collection is None:
            scored: list[dict[str, Any]] = []
            for uid, (vec, meta) in self._fallback_store.items():
                if exclude_note and meta.get("note_path") == exclude_note:
                    continue
                score = _cosine(query_vector, vec)
                scored.append({"block_uid": uid, "semantic_score": score, "note_path": meta.get("note_path")})
            scored.sort(key=lambda x: x["semantic_score"], reverse=True)
            return scored[:top_k]
        params = {"metric_type": "COSINE", "params": {"ef": 64}}
        expr = f'note_path != "{exclude_note}"' if exclude_note else None
        result = self._collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=params,
            limit=top_k,
            expr=expr,
            output_fields=["note_path"],
        )
        out: list[dict[str, Any]] = []
        for hit in result[0]:
            out.append(
                {
                    "block_uid": hit.id,
                    "semantic_score": float(hit.score),
                    "note_path": hit.entity.get("note_path"),
                }
            )
        return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
