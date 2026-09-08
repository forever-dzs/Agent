from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class FeishuKnowledgeClient:
    """封装飞书知识库访问逻辑，支持目录树遍历和文档读取。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.feishu_knowledge_base_url
        self.root_token = self.settings.feishu_knowledge_root_token
        self.token = self.settings.feishu_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        response = httpx.request(method=method, url=url, headers=self.headers, timeout=30, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") not in (0, None):
            raise RuntimeError(f"Feishu API error: {payload}")
        return payload.get("data", payload)

    def get_folder_tree(self) -> List[Dict[str, Any]]:
        """获取知识库目录树，按业务需要递归遍历。"""
        if not self.root_token:
            return []

        url = f"{self.base_url}/folder/tree"
        params = {"folder_token": self.root_token}
        data = self._request("GET", url, params=params)
        items = data.get("items") if isinstance(data, dict) else []
        return items or []

    def get_document_content(self, file_token: str) -> str:
        """读取文档内容。飞书返回的内容结构可能是文本、富文本等，统一抽取正文。"""
        if not file_token:
            return ""

        try:
            url = f"{self.base_url}/doc/content"
            data = self._request("GET", url, params={"document_id": file_token})
            if isinstance(data, dict):
                return self._extract_text_from_doc_payload(data)
        except Exception as exc:  # pragma: no cover - 边界保护
            logger.warning("Failed to fetch document %s: %s", file_token, exc)
        return ""

    def _extract_text_from_doc_payload(self, payload: Dict[str, Any]) -> str:
        """提取文本内容，兼容多种飞书文档结构。"""
        if not isinstance(payload, dict):
            return ""

        blocks = payload.get("body", {}).get("blocks") or payload.get("blocks") or []
        if isinstance(blocks, list):
            texts: List[str] = []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    texts.append(text)
                elif isinstance(text, list):
                    texts.append("".join(str(item) for item in text))
            return "\n".join(texts)

        return str(payload.get("content") or payload.get("text") or "")

    def iter_files(self, folder_token: str) -> List[Dict[str, Any]]:
        """递归入口：返回目录下文件列表，便于后续分块与索引。"""
        url = f"{self.base_url}/folder/files"
        payload = self._request("GET", url, params={"folder_token": folder_token})
        items = payload.get("items", []) if isinstance(payload, dict) else []
        return items if isinstance(items, list) else []
