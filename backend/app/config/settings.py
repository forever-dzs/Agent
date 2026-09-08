from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """统一配置入口。所有与运行环境相关的敏感或可变参数都在这里集中维护。"""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    app_name: str = Field(default="enterprise-knowledge-chat")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:5173")

    feishu_app_id: str = Field(default="")
    feishu_app_secret: str = Field(default="")
    feishu_knowledge_base_url: str = Field(default="")
    feishu_knowledge_root_token: str = Field(default="")
    feishu_token: str = Field(default="")

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    llm_primary_model: str = Field(default="gpt-4o-mini")
    llm_router_model: str = Field(default="gpt-4o-mini")
    llm_summary_model: str = Field(default="gpt-4o-mini")
    embedding_model: str = Field(default="text-embedding-3-small")

    milvus_uri: str = Field(default="http://localhost:19530")
    milvus_token: str = Field(default="")
    milvus_collection: str = Field(default="enterprise_knowledge")
    milvus_dimension: int = Field(default=1536)

    retrieval_top_k: int = Field(default=8)
    retrieval_score_threshold: float = Field(default=0.15)
    cache_ttl_seconds: int = Field(default=1800)
    cache_max_entries: int = Field(default=500)
    chunk_size: int = Field(default=1200)
    chunk_overlap: int = Field(default=200)

    frontend_port: int = Field(default=5173)
    vite_api_base_url: str = Field(default="http://localhost:8000")

    @property
    def cors_origins_list(self) -> List[str]:
        """将逗号分隔的跨域配置转成列表。"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """使用缓存避免重复读环境变量。"""
    return Settings()
