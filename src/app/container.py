from __future__ import annotations

from dataclasses import dataclass

from app.config import AppSettings, load_settings
from indexing.embedder import Embedder
from indexing.embedder_openai import OpenAIEmbedder
from indexing.embedder_wanqing import WanqingEmbedder
from indexing.sync_service import IndexSyncService
from query.retriever import Retriever
from query.service import QueryService
from storage.milvus_repo import MilvusRepo
from storage.sqlite_repo import SQLiteRepo


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    sqlite_repo: SQLiteRepo
    milvus_repo: MilvusRepo
    embedder: Embedder
    sync_service: IndexSyncService
    query_service: QueryService


def build_container() -> AppContainer:
    settings = load_settings()
    return build_container_from_settings(settings)


def build_container_from_settings(settings: AppSettings) -> AppContainer:
    sqlite_repo = SQLiteRepo(settings.sqlite_path)
    embedder: Embedder
    if settings.embedding_provider == "wanqing":
        embedder = WanqingEmbedder(
            api_key=settings.wanqing_api_key,
            model=settings.wanqing_model,
            dimensions=settings.embedding_dimensions,
            endpoint_url=settings.wanqing_base_url,
            batch_size=settings.embedding_batch_size,
            allow_pseudo_fallback=settings.allow_pseudo_embedding_fallback,
        )
    else:
        embedder = OpenAIEmbedder(
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            base_url=settings.embedding_base_url,
            batch_size=settings.embedding_batch_size,
            allow_pseudo_fallback=settings.allow_pseudo_embedding_fallback,
        )
    milvus_repo = MilvusRepo(
        uri=settings.milvus_uri,
        collection_name=settings.milvus_collection,
        dims=settings.embedding_dimensions or 1536,
    )
    sync_service = IndexSyncService(settings, sqlite_repo, milvus_repo, embedder)
    retriever = Retriever(settings, sqlite_repo, milvus_repo, embedder)
    query_service = QueryService(settings, sqlite_repo, retriever)
    return AppContainer(
        settings=settings,
        sqlite_repo=sqlite_repo,
        milvus_repo=milvus_repo,
        embedder=embedder,
        sync_service=sync_service,
        query_service=query_service,
    )
