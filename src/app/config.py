from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class BlockSplitConfig(BaseModel):
    min_chars: int = 80
    max_chars: int = 1200
    window_mode: Literal["SELF", "SELF_HEADING", "SLIDING"] = "SELF_HEADING"
    window_neighbors: int = 1
    index_code_blocks: bool = True


class RetrievalWeights(BaseModel):
    sem: float = 0.72
    lex: float = 0.18
    graph: float = 0.05
    synergy: float = 0.05


class QueryExpansionConfig(BaseModel):
    enabled: bool = True
    max_variants: int = 4
    min_token_length: int = 2


class RetrievalConfig(BaseModel):
    top_k: int = 10
    top_k_ann: int = 80
    threshold: float = 0.55
    dedup_sim_threshold: float = 0.98
    group_by_note: bool = True
    max_hits_per_note: int = 2
    note_diversity_penalty: float = 0.08
    min_lexical_gate: float = 0.2
    min_content_anchor: float = 0.08
    anchor_penalty_strength: float = 0.65
    semantic_only_anchor_floor: float = 0.12
    query_expansion: QueryExpansionConfig = Field(default_factory=QueryExpansionConfig)
    weights: RetrievalWeights = Field(default_factory=RetrievalWeights)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OBS_", extra="ignore")

    app_name: str = "obsidian-search"
    env: str = "dev"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    api_token: str | None = None
    vault_path: Path = Path(".")
    sqlite_path: Path = Path("./data/meta.db")
    milvus_uri: str = "http://localhost:19530"
    milvus_collection: str = "obsidian_blocks"
    embedding_provider: Literal["qianwen", "wanqing"] = "qianwen"
    embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int | None = 1024
    embedding_batch_size: int = 10
    allow_pseudo_embedding_fallback: bool = False
    embedding_api_key: str | None = None
    embedding_base_url: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    wanqing_api_key: str | None = None
    wanqing_model: str = "ep-3qt632-1773306339042123367"
    wanqing_base_url: str = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
    include_glob: list[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude_glob: list[str] = Field(
        default_factory=lambda: ["**/.obsidian/**", "**/.trash/**", "**/node_modules/**"]
    )
    exclude_dirs: list[str] = Field(default_factory=list)
    block_split: BlockSplitConfig = Field(default_factory=BlockSplitConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    poll_interval_sec: int = 5
    reindex_debounce_ms: int = 800

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_file = os.getenv("OBS_CONFIG_FILE")
        json_files: tuple[str, ...] | str = config_file or ("config.json", "settings.json")
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            JsonConfigSettingsSource(settings_cls, json_file=json_files),
        )


def load_settings() -> AppSettings:
    return AppSettings()
