from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.config.settings import get_settings
from app.core.cache import TTLCache
from app.services.feishu_client import FeishuKnowledgeClient
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    question: str
    conversation_id: str
    history: List[str]
    messages: List[Any]
    answer: str
    sources: List[Dict[str, Any]]
    cached: bool
    tool_steps: int


class KnowledgeAgentService:
    """真正的 ReAct 风格代理：模型先思考，再调用工具，最后根据工具观察结果生成答案。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache = TTLCache(ttl_seconds=self.settings.cache_ttl_seconds, max_entries=self.settings.cache_max_entries)
        self.vector_store = VectorStoreService()
        self.feishu_client = FeishuKnowledgeClient()
        self.llm_service = LLMService()
        self.knowledge_tool = StructuredTool.from_function(
            func=self._knowledge_search_tool,
            name="knowledge_search_tool",
            description=(
                "Search the enterprise knowledge base using semantic retrieval. "
                "Use this tool when the user asks about company policies, procedures, documents, or internal knowledge."
            ),
        )
        self.folder_tool = StructuredTool.from_function(
            func=self._folder_inspect_tool,
            name="knowledge_folder_tool",
            description=(
                "Inspect the Feishu knowledge base folder tree to find relevant document groups before searching. "
                "Use this when the user asks about a specific department, approval process, or a document category."
            ),
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        if self.llm_service.primary_model is None:
            return None

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "end": END,
            },
        )
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=MemorySaver())

    def _agent_node(self, state: AgentState) -> AgentState:
        if self.llm_service.primary_model is None:
            state["answer"] = (
                "当前系统尚未配置 OpenAI API Key，因此无法实际执行 ReAct 推理。"
                "请先在 .env 中补充真实的模型配置后再试。"
            )
            state["sources"] = []
            state["cached"] = False
            return state

        model = self.llm_service.primary_model.bind_tools([self.knowledge_tool, self.folder_tool])
        response = model.invoke(state["messages"])
        state["messages"].append(response)
        return state

    def _tool_node(self, state: AgentState) -> AgentState:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", None) or []
        if not tool_calls:
            state["answer"] = "没有需要执行的工具调用。"
            return state

        state["tool_steps"] = int(state.get("tool_steps", 0)) + 1
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("args", {}) or {}
            query = arguments.get("query") or state["question"]

            if tool_name == "knowledge_search_tool":
                tool_result = self._knowledge_search_tool(query)
            elif tool_name == "knowledge_folder_tool":
                tool_result = self._folder_inspect_tool(query)
            else:
                tool_result = json.dumps({"status": "unsupported", "results": []}, ensure_ascii=False)

            message = ToolMessage(
                content=tool_result,
                tool_call_id=tool_call.get("id", f"tool_call_{state['tool_steps']}"),
                name=tool_name,
            )
            state["messages"].append(message)

        return state

    def _should_continue(self, state: AgentState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return "end"

        if int(state.get("tool_steps", 0)) >= 2:
            return "end"

        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", []) or []
        return "tools" if tool_calls else "end"

    def _knowledge_search_tool(self, query: str) -> str:
        """真正的检索工具：调用 Milvus 召回最相关知识。"""
        if self.vector_store is None or not self.vector_store.available:
            return json.dumps({"status": "unavailable", "results": []}, ensure_ascii=False)

        docs = self.vector_store.similarity_search(query, k=self.settings.retrieval_top_k)
        payload = []
        for doc in docs:
            payload.append(
                {
                    "title": doc.metadata.get("title", "unknown"),
                    "content": doc.page_content[:800],
                    "source": doc.metadata.get("source", ""),
                    "score": round(float(doc.metadata.get("score", 0.0) or 0.0), 4),
                    "metadata": doc.metadata,
                }
            )
        return json.dumps({"status": "ok", "results": payload}, ensure_ascii=False)

    def _folder_inspect_tool(self, query: str) -> str:
        """查看飞书知识库目录树，帮助模型定位相关文档分组。"""
        try:
            folders = self.feishu_client.get_folder_tree()
            preview = []
            for folder in folders[:10]:
                preview.append(
                    {
                        "name": folder.get("name", "unknown"),
                        "type": folder.get("type", "folder"),
                        "token": folder.get("token", ""),
                    }
                )
            return json.dumps({"status": "ok", "query": query, "folders": preview}, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover
            logger.warning("Knowledge folder tool failed: %s", exc)
            return json.dumps({"status": "error", "query": query, "folders": []}, ensure_ascii=False)

    def _build_history_messages(self, question: str, history: List[str]) -> List[Any]:
        messages: List[Any] = []
        for item in history:
            if ": " not in item:
                messages.append(HumanMessage(content=item))
                continue
            role, content = item.split(": ", 1)
            role = role.strip().lower()
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        messages.append(HumanMessage(content=question))
        return messages

    def _extract_final_answer(self, messages: List[Any]) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                content = message.content
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    text_chunks = []
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_chunks.append(str(item["text"]))
                    if text_chunks:
                        return "\n".join(text_chunks)
        return "我已经分析了当前上下文，但未能提取出可直接回答的结论。"

    def _extract_sources(self, messages: List[Any]) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, ToolMessage):
                continue
            content = message.content
            if not isinstance(content, str):
                continue
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and "results" in payload:
                results = payload.get("results", []) or []
            elif isinstance(payload, list):
                results = payload
            else:
                continue

            for item in results:
                if isinstance(item, dict):
                    sources.append(
                        {
                            "title": item.get("title", "unknown"),
                            "content": item.get("content", ""),
                            "source": item.get("source", ""),
                            "score": float(item.get("score", 0.0) or 0.0),
                            "metadata": item.get("metadata", {}),
                        }
                    )
        return sources

    def _make_cache_key(self, question: str) -> str:
        return hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()

    def query(self, question: str, history: List[str], conversation_id: str) -> Dict[str, Any]:
        """对外暴露统一查询入口，采用显式 ReAct 循环：工具调用 -> 观察 -> 再推理，并持久化到会话记忆。"""
        cache_key = self._make_cache_key(question)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return {
                "answer": cached["answer"],
                "sources": cached["sources"],
                "cached": True,
                "conversation_id": conversation_id,
                "model_used": self.settings.llm_primary_model,
            }

        if self.llm_service.primary_model is None:
            return {
                "answer": (
                    "当前系统未配置有效大模型与知识库连接，无法执行真正的 ReAct 检索。"
                    "请在 .env 中配置 OpenAI API Key 和 Milvus/Feishu 相关信息。"
                ),
                "sources": [],
                "cached": False,
                "conversation_id": conversation_id,
                "model_used": self.settings.llm_primary_model,
            }

        config = {"configurable": {"thread_id": conversation_id}}
        prior_state = self.graph.get_state(config=config) if self.graph is not None else None
        prior_messages = []
        if prior_state is not None and prior_state.values:
            prior_messages = prior_state.values.get("messages", [])

        messages = self._build_history_messages(question, history)
        if prior_messages:
            seen = {str(getattr(message, "id", "")) for message in prior_messages if hasattr(message, "id")}
            for message in prior_messages:
                if hasattr(message, "content") and not str(getattr(message, "id", "")) in seen:
                    messages.insert(0, message)

        initial_state: AgentState = {
            "question": question,
            "conversation_id": conversation_id,
            "history": history,
            "messages": messages,
            "answer": "",
            "sources": [],
            "cached": False,
            "tool_steps": 0,
        }

        final_state = self.graph.invoke(initial_state, config=config) if self.graph is not None else initial_state
        final_state["answer"] = final_state.get("answer") or self._extract_final_answer(final_state.get("messages", []))
        final_state["sources"] = final_state.get("sources") or self._extract_sources(final_state.get("messages", []))

        answer = final_state["answer"]
        sources = final_state["sources"]

        if not answer or answer == "我已经分析了当前上下文，但未能提取出可直接回答的结论。":
            context = [
                f"标题：{item['title']}\n来源：{item['source']}\n内容：{item['content']}"
                for item in sources[:5]
            ]
            answer = self.llm_service.generate_answer(
                question=question,
                context_docs=context,
                history=history,
            )

        self.cache.set(cache_key, {"answer": answer, "sources": sources})
        return {
            "answer": answer,
            "sources": sources,
            "cached": False,
            "conversation_id": conversation_id,
            "model_used": self.settings.llm_primary_model,
        }

    def _serialize_doc(self, doc: Document) -> str:
        title = doc.metadata.get("title", "unknown")
        source = doc.metadata.get("source", "")
        return f"标题：{title}\n来源：{source}\n内容：{doc.page_content}"
