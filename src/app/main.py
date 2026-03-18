from __future__ import annotations

import logging
from time import perf_counter

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from api.routes.index import router as index_router
from api.routes.query import router as query_router
from api.routes.ui import router as ui_router
from app.container import build_container

REQUEST_COUNT = Counter("http_requests_total", "Total request count", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_seconds", "Request latency seconds", ["method", "path"])
logger = logging.getLogger("obsidian_search.app")


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app = FastAPI(title="Obsidian Search API", version="0.1.0")
    app.state.container = build_container()
    logger.info("app started vault=%s sqlite=%s", app.state.container.settings.vault_path, app.state.container.settings.sqlite_path)
    app.include_router(ui_router)
    app.include_router(index_router)
    app.include_router(query_router)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        started = perf_counter()
        response = await call_next(request)
        elapsed = perf_counter() - started
        REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        return response

    @app.get("/health")
    def health() -> dict:
        status = app.state.container.sqlite_repo.latest_status()
        return {
            "status": "ok",
            "storage": status,
            "milvus_backend": app.state.container.milvus_repo.backend(),
            "milvus_uri": app.state.container.settings.milvus_uri,
        }

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
