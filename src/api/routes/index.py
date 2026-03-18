from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from api.schemas import IndexFileRequest
from app.deps import require_token
from indexing.diff import collect_markdown_files

router = APIRouter(prefix="/v1/index", tags=["index"])
logger = logging.getLogger("obsidian_search.api.index")


@router.post("/rebuild", dependencies=[Depends(require_token)])
def rebuild_index(request: Request, background_tasks: BackgroundTasks) -> dict:
    container = request.app.state.container
    logger.info("api rebuild requested")
    job_id = container.sqlite_repo.log_job(
        "rebuild",
        "queued",
        {"current_file": 0, "total_files": 0, "indexed_files": 0, "failed_files": 0, "elapsed_ms": 0},
    )
    background_tasks.add_task(container.sync_service.rebuild, job_id)
    return {"job_id": job_id, "status": "queued"}


@router.post("/sync", dependencies=[Depends(require_token)])
def sync_index(request: Request) -> dict:
    container = request.app.state.container
    logger.info("api sync requested")
    return container.sync_service.sync()


@router.post("/clear", dependencies=[Depends(require_token)])
def clear_index(request: Request) -> dict:
    container = request.app.state.container
    logger.info("api clear requested")
    return container.sync_service.clear()


@router.post("/file", dependencies=[Depends(require_token)])
def index_file(payload: IndexFileRequest, request: Request) -> dict:
    container = request.app.state.container
    logger.info("api index_file requested note_path=%s", payload.note_path)
    return container.sync_service.index_file(payload.note_path)


@router.get("/status")
def index_status(request: Request) -> dict:
    container = request.app.state.container
    status = container.sqlite_repo.latest_status()
    status["vault_path"] = str(container.settings.vault_path)
    status["sqlite_path"] = str(container.settings.sqlite_path)
    status["milvus_uri"] = container.settings.milvus_uri
    status["milvus_collection"] = container.settings.milvus_collection
    status["milvus_backend"] = container.milvus_repo.backend()
    return status


@router.get("/job/{job_id}")
def job_status(job_id: int, request: Request) -> dict:
    container = request.app.state.container
    row = container.sqlite_repo.get_job(job_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    detail_raw = row["detail"] or "{}"
    try:
        detail = json.loads(detail_raw)
    except Exception:
        detail = {"raw": detail_raw}
    return {
        "id": row["id"],
        "job_type": row["job_type"],
        "status": row["status"],
        "detail": detail,
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
    }


@router.get("/dashboard")
def dashboard_stats(request: Request) -> dict:
    container = request.app.state.container
    status = container.sqlite_repo.latest_status()
    vault_files = collect_markdown_files(
        container.settings.vault_path,
        container.settings.include_glob,
        container.settings.exclude_glob,
        container.settings.exclude_dirs,
    )
    return {
        "target_directory": str(container.settings.vault_path),
        "vault_markdown_files": len(vault_files),
        "indexed_files": status.get("note_count", 0),
        "indexed_blocks": status.get("block_count", 0),
        "last_job": status.get("last_job"),
    }
