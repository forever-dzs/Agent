from __future__ import annotations

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Milvus 向量库封装，负责创建索引和相似度搜索。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.embeddings: Optional[OpenAIEmbeddings] = None
        self.vector_store: Optional[Milvus] = None
        self.available = False

        if not self.settings.openai_api_key:
            logger.warning("OpenAI API key is not configured; vector search is temporarily unavailable.")
            return

        try:
            self.embeddings = OpenAIEmbeddings(
                model=self.settings.embedding_model,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
            self.vector_store = Milvus(
                embedding_function=self.embeddings,
                collection_name=self.settings.milvus_collection,
                connection_args={"uri": self.settings.milvus_uri, "token": self.settings.milvus_token},
                index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}},
                search_params={"metric_type": "L2", "params": {"nprobe": 10}},
                auto_id=True,
            )
            self.available = True
        except Exception as exc:  # pragma: no cover - 允许未部署 Milvus 时应用仍可启动
            logger.warning("Milvus is unavailable or misconfigured: %s", exc)
            self.vector_store = None
            self.available = False

    def add_documents(self, documents: List[Document]) -> None:
        if not documents or not self.available or self.vector_store is None:
            return
        self.vector_store.add_documents(documents)
        logger.info("Indexed %s documents to Milvus", len(documents))

    def similarity_search(self, query: str, k: Optional[int] = None) -> List[Document]:
        if not self.available or self.vector_store is None:
            return []
        top_k = k or self.settings.retrieval_top_k
        return self.vector_store.similarity_search(query, k=top_k)
