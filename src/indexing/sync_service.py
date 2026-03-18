from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from app.config import AppSettings
from app.models import NoteDoc
from indexing.diff import collect_markdown_files, compute_file_diff, is_path_excluded
from indexing.embedder import Embedder
from indexing.parser import parse_markdown_file
from indexing.splitter import build_embedding_inputs, split_note_into_blocks
from storage.milvus_repo import MilvusRepo
from storage.sqlite_repo import SQLiteRepo

logger = logging.getLogger("obsidian_search.index")


class IndexSyncService:
    def __init__(
        self,
        settings: AppSettings,
        sqlite_repo: SQLiteRepo,
        milvus_repo: MilvusRepo,
        embedder: Embedder,
    ) -> None:
        self._settings = settings
        self._sqlite = sqlite_repo
        self._milvus = milvus_repo
        self._embedder = embedder

    def rebuild(self, job_id: int | None = None) -> dict[str, Any]:
        if job_id is None:
            job_id = self._sqlite.log_job("rebuild", "running", {})
        else:
            self._sqlite.update_job(job_id, status="running", detail={})
        started = perf_counter()
        paths = collect_markdown_files(
            self._settings.vault_path,
            self._settings.include_glob,
            self._settings.exclude_glob,
            self._settings.exclude_dirs,
        )
        total_files = len(paths)
        self._sqlite.update_job(
            job_id,
            detail={
                "current_file": 0,
                "total_files": total_files,
                "indexed_files": 0,
                "failed_files": 0,
                "elapsed_ms": 0,
            },
        )
        logger.info("rebuild started job_id=%s files=%s vault=%s", job_id, len(paths), self._settings.vault_path)
        indexed = 0
        failures: list[dict[str, str]] = []
        try:
            for i, p in enumerate(paths, start=1):
                try:
                    self._index_single_file(p)
                    indexed += 1
                except Exception as exc:  # pragma: no cover
                    logger.exception("rebuild file failed path=%s", p)
                    failures.append({"path": str(p), "error": str(exc)})
                self._sqlite.update_job(
                    job_id,
                    detail={
                        "current_file": i,
                        "total_files": total_files,
                        "indexed_files": indexed,
                        "failed_files": len(failures),
                        "elapsed_ms": int((perf_counter() - started) * 1000),
                    },
                )
            elapsed_ms = int((perf_counter() - started) * 1000)
            detail = {
                "current_file": total_files,
                "total_files": total_files,
                "indexed_files": indexed,
                "failed_files": len(failures),
                "elapsed_ms": elapsed_ms,
            }
            if failures:
                detail["failures"] = failures[:20]
            if failures and indexed == 0:
                status = "failed"
            elif failures:
                status = "partial_success"
            else:
                status = "success"
            self._sqlite.finish_job(job_id, status, detail)
            logger.info("rebuild finished job_id=%s status=%s indexed=%s failed=%s elapsed_ms=%s", job_id, status, indexed, len(failures), elapsed_ms)
            return {"job_id": job_id, "status": status, **detail}
        except Exception as exc:  # pragma: no cover
            elapsed_ms = int((perf_counter() - started) * 1000)
            detail = {"error": str(exc), "indexed_files": indexed, "elapsed_ms": elapsed_ms}
            self._sqlite.finish_job(job_id, "failed", detail)
            logger.exception("rebuild failed job_id=%s elapsed_ms=%s", job_id, elapsed_ms)
            raise

    def sync(self) -> dict[str, Any]:
        job_id = self._sqlite.log_job("sync", "running", {})
        started = perf_counter()
        current_paths = collect_markdown_files(
            self._settings.vault_path,
            self._settings.include_glob,
            self._settings.exclude_glob,
            self._settings.exclude_dirs,
        )
        logger.info("sync started job_id=%s scanned_files=%s", job_id, len(current_paths))
        try:
            current = {
                str(p.relative_to(self._settings.vault_path)): parse_markdown_file(p, self._settings.vault_path).content_hash
                for p in current_paths
            }
            existing = {row["path"]: row["content_hash"] for row in self._sqlite.list_notes()}
            diff = compute_file_diff(current=current, existing=existing)
            logger.info(
                "sync diff job_id=%s added=%s modified=%s deleted=%s",
                job_id,
                len(diff["added"]),
                len(diff["modified"]),
                len(diff["deleted"]),
            )
            indexed = 0
            for rel_path in diff["added"] + diff["modified"]:
                self._index_single_file(self._settings.vault_path / rel_path)
                indexed += 1
            deleted_blocks = 0
            for rel_path in diff["deleted"]:
                rows = self._sqlite.get_blocks_by_note(rel_path)
                deleted_blocks += len(rows)
                self._milvus.delete([r["block_uid"] for r in rows])
                self._sqlite.delete_note(rel_path)
            elapsed_ms = int((perf_counter() - started) * 1000)
            detail = {
                "changes": diff,
                "indexed_files": indexed,
                "deleted_blocks": deleted_blocks,
                "elapsed_ms": elapsed_ms,
            }
            self._sqlite.finish_job(job_id, "success", detail)
            logger.info(
                "sync finished job_id=%s indexed=%s deleted_blocks=%s elapsed_ms=%s",
                job_id,
                indexed,
                deleted_blocks,
                elapsed_ms,
            )
            return {"job_id": job_id, "status": "success", **detail}
        except Exception as exc:  # pragma: no cover
            elapsed_ms = int((perf_counter() - started) * 1000)
            self._sqlite.finish_job(job_id, "failed", {"error": str(exc), "elapsed_ms": elapsed_ms})
            logger.exception("sync failed job_id=%s elapsed_ms=%s", job_id, elapsed_ms)
            raise

    def clear(self) -> dict[str, Any]:
        logger.info("clear index started")
        started = perf_counter()
        job_id = self._sqlite.log_job("clear", "running", {})
        try:
            sqlite_deleted = self._sqlite.clear_index_data()
            self._milvus.clear()
            elapsed_ms = int((perf_counter() - started) * 1000)
            detail = {"deleted": sqlite_deleted, "elapsed_ms": elapsed_ms}
            self._sqlite.finish_job(job_id, "success", detail)
            logger.info("clear index finished job_id=%s deleted=%s elapsed_ms=%s", job_id, sqlite_deleted, elapsed_ms)
            return {"job_id": job_id, "status": "success", **detail}
        except Exception as exc:  # pragma: no cover
            elapsed_ms = int((perf_counter() - started) * 1000)
            detail = {"error": str(exc), "elapsed_ms": elapsed_ms}
            self._sqlite.finish_job(job_id, "failed", detail)
            logger.exception("clear index failed job_id=%s elapsed_ms=%s", job_id, elapsed_ms)
            raise

    def index_file(self, rel_path: str) -> dict[str, Any]:
        p = self._settings.vault_path / rel_path
        if is_path_excluded(
            p,
            self._settings.vault_path,
            self._settings.exclude_glob,
            self._settings.exclude_dirs,
        ):
            logger.info("index_file skipped by exclude rules path=%s", rel_path)
            return {"skipped": rel_path, "reason": "excluded"}
        logger.info("index_file started path=%s", rel_path)
        started = perf_counter()
        self._index_single_file(p)
        elapsed_ms = int((perf_counter() - started) * 1000)
        logger.info("index_file finished path=%s elapsed_ms=%s", rel_path, elapsed_ms)
        return {"indexed": rel_path, "elapsed_ms": elapsed_ms}

    def _index_single_file(self, path: Path) -> NoteDoc:
        started = perf_counter()
        note = parse_markdown_file(path, self._settings.vault_path)
        old_blocks = self._sqlite.get_blocks_by_note(note.path)
        blocks = split_note_into_blocks(note, self._settings.block_split)
        embedding_inputs = build_embedding_inputs(blocks, self._settings.block_split)
        vecs = self._embedder.embed_texts(embedding_inputs)
        for b, vec, emb_text in zip(blocks, vecs, embedding_inputs):
            b.metadata["embedding_dim"] = len(vec)
            b.metadata["embedding_input_len"] = len(emb_text)
            b.metadata["embedding_window_mode"] = self._settings.block_split.window_mode
        note.blocks = blocks
        self._sqlite.upsert_note(note)
        self._milvus.delete([r["block_uid"] for r in old_blocks])
        self._sqlite.replace_note_blocks(note.path, blocks)
        self._sqlite.replace_note_links(note.path, note.links)
        self._milvus.upsert(
            {"block_uid": b.block_uid, "embedding": vec, "note_path": b.note_path}
            for b, vec in zip(blocks, vecs)
        )
        elapsed_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "indexed file=%s blocks_new=%s blocks_old=%s vectors=%s elapsed_ms=%s",
            note.path,
            len(blocks),
            len(old_blocks),
            len(vecs),
            elapsed_ms,
        )
        return note
