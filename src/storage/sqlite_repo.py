from __future__ import annotations

import json
import math
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models import Block, LinkRef, NoteDoc

COMMON_STOPWORDS = {
    "api",
    "http",
    "https",
    "www",
    "com",
    "org",
    "net",
    "rest",
    "json",
    "xml",
    "get",
    "post",
    "put",
    "delete",
    "管理",
    "系统",
    "模块",
    "接口",
    "服务",
    "功能",
    "方案",
    "流程",
    "问题",
    "方法",
    "数据",
    "设计",
    "开发",
}
ASCII_TOKEN_RE = re.compile(r"^[0-9A-Za-z_]+$")


class SQLiteRepo:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._token_df_cache: dict[str, int] = {}
        self._total_block_count_cache: int | None = None
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS notes (
              note_id INTEGER PRIMARY KEY AUTOINCREMENT,
              path TEXT UNIQUE NOT NULL,
              title TEXT NOT NULL,
              aliases TEXT NOT NULL,
              tags TEXT NOT NULL,
              frontmatter TEXT NOT NULL,
              mtime REAL NOT NULL,
              content_hash TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS blocks (
              block_uid TEXT PRIMARY KEY,
              note_path TEXT NOT NULL,
              block_id TEXT NOT NULL,
              heading_path TEXT NOT NULL,
              raw_text TEXT NOT NULL,
              clean_text TEXT NOT NULL,
              char_start INTEGER NOT NULL,
              char_end INTEGER NOT NULL,
              token_count_est INTEGER NOT NULL,
              block_hash TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              metadata TEXT NOT NULL,
              FOREIGN KEY(note_path) REFERENCES notes(path) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_blocks_note_path ON blocks(note_path);
            CREATE INDEX IF NOT EXISTS idx_blocks_block_hash ON blocks(block_hash);

            CREATE TABLE IF NOT EXISTS links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              src_note_path TEXT NOT NULL,
              src_block_uid TEXT,
              dst_note_path TEXT NOT NULL,
              dst_heading TEXT,
              dst_block_id TEXT,
              link_text TEXT,
              type TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_links_src_note ON links(src_note_path);
            CREATE INDEX IF NOT EXISTS idx_links_dst_note ON links(dst_note_path);

            CREATE TABLE IF NOT EXISTS index_jobs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_type TEXT NOT NULL,
              status TEXT NOT NULL,
              detail TEXT NOT NULL,
              created_at TEXT NOT NULL,
              finished_at TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts
            USING fts5(block_uid UNINDEXED, clean_text, note_path UNINDEXED, tokenize='porter');
            """
        )
        self._conn.commit()

    def upsert_note(self, doc: NoteDoc) -> None:
        self._conn.execute(
            """
            INSERT INTO notes(path, title, aliases, tags, frontmatter, mtime, content_hash, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
              title = excluded.title,
              aliases = excluded.aliases,
              tags = excluded.tags,
              frontmatter = excluded.frontmatter,
              mtime = excluded.mtime,
              content_hash = excluded.content_hash,
              updated_at = excluded.updated_at
            """,
            (
                doc.path,
                doc.title,
                json.dumps(doc.aliases, ensure_ascii=False),
                json.dumps(doc.tags, ensure_ascii=False),
                json.dumps(doc.frontmatter, ensure_ascii=False),
                doc.mtime,
                doc.content_hash,
                datetime.utcnow().isoformat(),
            ),
        )
        self._conn.commit()

    def replace_note_blocks(self, note_path: str, blocks: Iterable[Block]) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM blocks WHERE note_path = ?", (note_path,))
        cur.execute("DELETE FROM blocks_fts WHERE note_path = ?", (note_path,))
        now = datetime.utcnow().isoformat()
        for block in blocks:
            cur.execute(
                """
                INSERT INTO blocks(
                  block_uid, note_path, block_id, heading_path, raw_text, clean_text,
                  char_start, char_end, token_count_est, block_hash, updated_at, metadata
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    block.block_uid,
                    block.note_path,
                    block.block_id,
                    json.dumps(block.heading_path, ensure_ascii=False),
                    block.raw_text,
                    block.clean_text,
                    block.char_start,
                    block.char_end,
                    block.token_count_est,
                    block.block_hash,
                    now,
                    json.dumps(block.metadata, ensure_ascii=False),
                ),
            )
            cur.execute(
                "INSERT INTO blocks_fts(block_uid, clean_text, note_path) VALUES (?, ?, ?)",
                (block.block_uid, block.clean_text, block.note_path),
            )
        self._conn.commit()
        self._invalidate_lexical_stats_cache()

    def replace_note_links(self, note_path: str, links: Iterable[LinkRef]) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM links WHERE src_note_path = ?", (note_path,))
        for link in links:
            cur.execute(
                """
                INSERT INTO links(
                  src_note_path, src_block_uid, dst_note_path, dst_heading, dst_block_id, link_text, type
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link.src_note_path,
                    link.src_block_uid,
                    link.dst_note_path,
                    link.dst_heading,
                    link.dst_block_id,
                    link.link_text,
                    link.link_type,
                ),
            )
        self._conn.commit()

    def delete_note(self, note_path: str) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM blocks_fts WHERE note_path = ?", (note_path,))
        cur.execute("DELETE FROM blocks WHERE note_path = ?", (note_path,))
        cur.execute("DELETE FROM links WHERE src_note_path = ? OR dst_note_path = ?", (note_path, note_path))
        cur.execute("DELETE FROM notes WHERE path = ?", (note_path,))
        self._conn.commit()
        self._invalidate_lexical_stats_cache()

    def list_notes(self) -> list[sqlite3.Row]:
        return list(self._conn.execute("SELECT * FROM notes"))

    def get_note(self, note_path: str) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM notes WHERE path = ?", (note_path,)).fetchone()

    def get_blocks_by_note(self, note_path: str) -> list[sqlite3.Row]:
        return list(self._conn.execute("SELECT * FROM blocks WHERE note_path = ? ORDER BY char_start", (note_path,)))

    def get_block(self, block_uid: str) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM blocks WHERE block_uid = ?", (block_uid,)).fetchone()

    def lexical_search(self, text: str, top_k: int) -> list[dict[str, Any]]:
        tokens = self._extract_query_tokens(text)
        if not tokens:
            return []
        tokens, token_weights = self._select_informative_tokens(tokens)
        if not tokens:
            return []
        query = " OR ".join(f'"{token}"' for token in tokens[:16])
        rows: list[sqlite3.Row] = []
        fetch_limit = max(top_k, top_k * 4)
        try:
            rows = self._run_fts_query(query, fetch_limit)
        except sqlite3.OperationalError:
            fallback_query = self._safe_fts_query(" ".join(tokens))
            if not fallback_query:
                return []
            try:
                rows = self._run_fts_query(fallback_query, fetch_limit)
            except sqlite3.OperationalError:
                return []
        if not rows:
            return self._like_fallback_search(tokens, token_weights, top_k)
        raw_scores = [float(r["bm25_score"]) for r in rows]
        max_s, min_s = max(raw_scores), min(raw_scores)
        span = (max_s - min_s) or 1.0
        total_weight = sum(token_weights.values()) or 1.0
        out: list[dict[str, Any]] = []
        for r in rows:
            score = float(r["bm25_score"])
            bm25_norm = 1.0 - ((score - min_s) / span)
            matched_weight = 0.0
            clean_text = str(r["clean_text"]).lower()
            for token, weight in token_weights.items():
                if self._token_in_text(token, clean_text):
                    matched_weight += weight
            coverage = matched_weight / total_weight
            combined = 0.7 * bm25_norm + 0.3 * coverage
            out.append({"block_uid": r["block_uid"], "note_path": r["note_path"], "lex_score": combined})
        out.sort(key=lambda x: x["lex_score"], reverse=True)
        return out[:top_k]

    def _run_fts_query(self, query: str, top_k: int) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                """
                SELECT block_uid, note_path, clean_text, bm25(blocks_fts) AS bm25_score
                FROM blocks_fts
                WHERE blocks_fts MATCH ?
                ORDER BY bm25_score
                LIMIT ?
                """,
                (query, top_k),
            ).fetchall()
        )

    def _safe_fts_query(self, text: str) -> str:
        # Keep only simple tokens to avoid FTS5 parser errors on user input.
        tokens = re.findall(r"[0-9A-Za-z_\u4e00-\u9fff]+", text)
        if not tokens:
            return ""
        unique_tokens = list(dict.fromkeys(tokens))
        return " OR ".join(f'"{token}"' for token in unique_tokens[:16])

    def _like_fallback_search(self, tokens: list[str], token_weights: dict[str, float], top_k: int) -> list[dict[str, Any]]:
        if not tokens:
            return []
        unique_tokens = list(dict.fromkeys(tokens))[:8]
        where_clause = " OR ".join(["clean_text LIKE ?"] * len(unique_tokens))
        params = [f"%{token}%" for token in unique_tokens]
        rows = self._conn.execute(
            f"""
            SELECT block_uid, note_path, clean_text
            FROM blocks
            WHERE {where_clause}
            LIMIT 500
            """,
            params,
        ).fetchall()
        if not rows:
            return []
        scored: list[dict[str, Any]] = []
        denom = float(sum(token_weights.get(token, 1.0) for token in unique_tokens)) or 1.0
        for r in rows:
            clean_text = str(r["clean_text"]).lower()
            matched_weight = 0.0
            for token in unique_tokens:
                if self._token_in_text(token, clean_text):
                    matched_weight += token_weights.get(token, 1.0)
            if matched_weight <= 0:
                continue
            scored.append(
                {
                    "block_uid": r["block_uid"],
                    "note_path": r["note_path"],
                    "lex_score": matched_weight / denom,
                }
            )
        scored.sort(key=lambda x: x["lex_score"], reverse=True)
        return scored[:top_k]

    def _extract_query_tokens(self, text: str) -> list[str]:
        if not text:
            return []
        raw_tokens = re.findall(r"[0-9A-Za-z_]+|[\u4e00-\u9fff]{2,}", text.lower())
        out: list[str] = []
        seen: set[str] = set()
        for token in raw_tokens:
            if token in seen:
                continue
            if ASCII_TOKEN_RE.match(token) and len(token) < 3:
                continue
            seen.add(token)
            out.append(token)
        return out

    def _select_informative_tokens(self, tokens: list[str]) -> tuple[list[str], dict[str, float]]:
        if not tokens:
            return [], {}
        total_blocks = self._total_block_count()
        stats: list[tuple[str, int]] = []
        for token in tokens:
            if token in COMMON_STOPWORDS:
                continue
            df = self._token_document_frequency(token)
            stats.append((token, df))
        if not stats:
            return [], {}
        informative: list[str] = []
        for token, df in stats:
            ratio = (df / total_blocks) if total_blocks > 0 else 0.0
            is_common = df >= 12 and ratio >= 0.25
            if not is_common:
                informative.append(token)
        if not informative:
            informative = [min(stats, key=lambda item: item[1])[0]]
        weights: dict[str, float] = {}
        for token in informative:
            df = next(v for t, v in stats if t == token)
            weights[token] = math.log((total_blocks + 1.0) / (df + 1.0)) + 1.0 if total_blocks > 0 else 1.0
        return informative, weights

    def _token_document_frequency(self, token: str) -> int:
        cached = self._token_df_cache.get(token)
        if cached is not None:
            return cached
        df = 0
        try:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM blocks_fts WHERE blocks_fts MATCH ?",
                (f'"{token}"',),
            ).fetchone()
            df = int(row[0]) if row is not None else 0
        except sqlite3.OperationalError:
            row = self._conn.execute("SELECT COUNT(*) FROM blocks WHERE clean_text LIKE ?", (f"%{token}%",)).fetchone()
            df = int(row[0]) if row is not None else 0
        self._token_df_cache[token] = df
        return df

    def _total_block_count(self) -> int:
        if self._total_block_count_cache is not None:
            return self._total_block_count_cache
        row = self._conn.execute("SELECT COUNT(*) FROM blocks").fetchone()
        self._total_block_count_cache = int(row[0]) if row is not None else 0
        return self._total_block_count_cache

    def _invalidate_lexical_stats_cache(self) -> None:
        self._token_df_cache.clear()
        self._total_block_count_cache = None

    def _token_in_text(self, token: str, text_lower: str) -> bool:
        if not token:
            return False
        if token in text_lower:
            if not ASCII_TOKEN_RE.match(token):
                return True
            return re.search(rf"(?<![0-9A-Za-z_]){re.escape(token)}(?![0-9A-Za-z_])", text_lower) is not None
        return False

    def log_job(self, job_type: str, status: str, detail: dict[str, Any]) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO index_jobs(job_type, status, detail, created_at)
            VALUES(?, ?, ?, ?)
            """,
            (job_type, status, json.dumps(detail, ensure_ascii=False), datetime.utcnow().isoformat()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def finish_job(self, job_id: int, status: str, detail: dict[str, Any]) -> None:
        self._conn.execute(
            "UPDATE index_jobs SET status = ?, detail = ?, finished_at = ? WHERE id = ?",
            (status, json.dumps(detail, ensure_ascii=False), datetime.utcnow().isoformat(), job_id),
        )
        self._conn.commit()

    def update_job(self, job_id: int, status: str | None = None, detail: dict[str, Any] | None = None) -> None:
        if status is None and detail is None:
            return
        if status is not None and detail is not None:
            self._conn.execute(
                "UPDATE index_jobs SET status = ?, detail = ? WHERE id = ?",
                (status, json.dumps(detail, ensure_ascii=False), job_id),
            )
        elif status is not None:
            self._conn.execute("UPDATE index_jobs SET status = ? WHERE id = ?", (status, job_id))
        else:
            self._conn.execute(
                "UPDATE index_jobs SET detail = ? WHERE id = ?",
                (json.dumps(detail, ensure_ascii=False), job_id),
            )
        self._conn.commit()

    def get_job(self, job_id: int) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM index_jobs WHERE id = ?", (job_id,)).fetchone()

    def latest_status(self) -> dict[str, Any]:
        jobs = list(self._conn.execute("SELECT * FROM index_jobs ORDER BY id DESC LIMIT 1"))
        note_count = self._conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        block_count = self._conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
        return {
            "note_count": note_count,
            "block_count": block_count,
            "last_job": dict(jobs[0]) if jobs else None,
        }

    def clear_index_data(self) -> dict[str, int]:
        note_count = int(self._conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
        block_count = int(self._conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0])
        link_count = int(self._conn.execute("SELECT COUNT(*) FROM links").fetchone()[0])
        cur = self._conn.cursor()
        cur.execute("DELETE FROM blocks_fts")
        cur.execute("DELETE FROM blocks")
        cur.execute("DELETE FROM links")
        cur.execute("DELETE FROM notes")
        self._conn.commit()
        self._invalidate_lexical_stats_cache()
        return {"notes": note_count, "blocks": block_count, "links": link_count}

    def links_from_note(self, src_note_path: str) -> list[sqlite3.Row]:
        return list(self._conn.execute("SELECT * FROM links WHERE src_note_path = ?", (src_note_path,)))

    def to_block(self, row: sqlite3.Row) -> Block:
        return Block(
            block_uid=row["block_uid"],
            note_path=row["note_path"],
            block_id=row["block_id"],
            heading_path=json.loads(row["heading_path"]),
            raw_text=row["raw_text"],
            clean_text=row["clean_text"],
            char_start=row["char_start"],
            char_end=row["char_end"],
            token_count_est=row["token_count_est"],
            block_hash=row["block_hash"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        self._conn.close()
