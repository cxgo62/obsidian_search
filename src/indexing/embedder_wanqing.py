from __future__ import annotations

import hashlib
import json
import logging
import math
from collections.abc import Iterable
from urllib import request

try:
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None  # type: ignore[assignment]

logger = logging.getLogger("obsidian_search.embedder")


class WanqingEmbedder:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        dimensions: int | None,
        endpoint_url: str,
        batch_size: int = 128,
        allow_pseudo_fallback: bool = False,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._endpoint_url = endpoint_url
        self._batch_size = batch_size
        self._allow_pseudo_fallback = allow_pseudo_fallback
        self._encoding = tiktoken.get_encoding("cl100k_base") if tiktoken else None

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        values = [t for t in texts if t.strip()]
        if not values:
            return []
        if not self._api_key:
            if not self._allow_pseudo_fallback:
                raise RuntimeError("wanqing embedding client unavailable: missing API key")
            return [_pseudo_embedding(t, self._dimensions or 256) for t in values]
        try:
            vectors: list[list[float]] = []
            for batch in _batch_by_count(values, self._batch_size):
                payload = {
                    "model": self._model,
                    "input": batch,
                    "encoding_format": "float",
                }
                resp = self._post_json(payload)
                vectors.extend(_extract_vectors(resp))
            return vectors
        except Exception as exc:  # pragma: no cover - network/quota/runtime dependent
            if not self._allow_pseudo_fallback:
                raise RuntimeError(f"wanqing embedding failed: {exc}") from exc
            logger.warning("wanqing embedding failed, fallback to pseudo embedding: %s", exc)
            return [_pseudo_embedding(t, self._dimensions or 256) for t in values]

    def estimate_tokens(self, text: str) -> int:
        if self._encoding is None:
            return max(1, len(text) // 4)
        return len(self._encoding.encode(text))

    def _post_json(self, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._endpoint_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req, timeout=20) as resp:  # noqa: S310 - configurable endpoint by design
            text = resp.read().decode("utf-8")
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("wanqing response is not an object")
            return data


def _extract_vectors(payload: dict[str, object]) -> list[list[float]]:
    data = payload.get("data")
    if isinstance(data, list):
        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            emb = item.get("embedding")
            if isinstance(emb, list):
                vectors.append([float(v) for v in emb])
        if vectors:
            return vectors

    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
        return [[float(v) for v in emb] for emb in embeddings]
    raise ValueError("unable to parse wanqing embeddings response")


def _batch_by_count(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def _pseudo_embedding(text: str, dims: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(dims):
        b = digest[i % len(digest)]
        values.append((b / 255.0) - 0.5)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]
