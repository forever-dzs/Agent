from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import get_settings
from app.services.feishu_client import FeishuKnowledgeClient

logger = logging.getLogger(__name__)


class DocumentIngestService:
    """负责飞书文档目录遍历、清洗、分块和标准化为 LangChain Document。"""

    def __init__(self, feishu_client: Optional[FeishuKnowledgeClient] = None):
        self.settings = get_settings()
        self.feishu_client = feishu_client or FeishuKnowledgeClient()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            separators=["\n\n", "\n", "。", "!", "?", " ", ""],
        )

    def fetch_all_documents(self) -> List[Document]:
        """从飞书根目录递归拉取全部文档并做标准化。"""
        documents: List[Document] = []
        root_tree = self.feishu_client.get_folder_tree()
        for folder in self._flatten_folders(root_tree):
            docs = self._collect_documents_from_folder(folder)
            documents.extend(docs)
        return documents

    def _flatten_folders(self, nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """递归展开目录树，保留层级关系。"""
        result: List[Dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("type") == "folder":
                result.append(node)
            children = node.get("children") or []
            if isinstance(children, list) and children:
                result.extend(self._flatten_folders(children))
        return result

    def _collect_documents_from_folder(self, folder: Dict[str, Any]) -> List[Document]:
        """遍历一个目录的文件，并从文档正文抽取出可检索的 chunk。"""
        folder_token = folder.get("token") or folder.get("folder_token")
        if not folder_token:
            return []

        files = self.feishu_client.iter_files(folder_token)
        documents: List[Document] = []
        for file in files:
            file_type = file.get("type")
            if file_type not in {"doc", "wiki", "sheet", "file"}:
                continue

            file_token = file.get("token") or file.get("file_token")
            title = file.get("title") or file.get("name") or "Untitled"
            source = file.get("url") or file.get("link") or str(file_token)
            content = self.feishu_client.get_document_content(file_token)
            if not content.strip():
                logger.warning("Skipping empty content for %s", title)
                continue

            chunked = self.splitter.split_text(content)
            for index, chunk in enumerate(chunked):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "title": title,
                        "source": source,
                        "folder": folder.get("name", "unknown"),
                        "document_token": file_token,
                        "chunk_index": index,
                    },
                )
                documents.append(doc)
        return documents
