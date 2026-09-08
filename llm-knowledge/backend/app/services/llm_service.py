from __future__ import annotations

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """封装大模型调用，支持轻量路由模型和强生成模型的分层管理。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.primary_model = None
        self.router_model = None

        if not self.settings.openai_api_key:
            logger.warning("OpenAI API key is not configured; LLM responses will fall back to safe placeholders.")
            return

        self.primary_model = ChatOpenAI(
            model=self.settings.llm_primary_model,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            temperature=0.2,
        )
        self.router_model = ChatOpenAI(
            model=self.settings.llm_router_model,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            temperature=0.0,
        )

    def route_question(self, question: str) -> str:
        """小模型负责识别问题类型，决定是否调用知识库检索。"""
        if self.router_model is None:
            return "RETRIEVE"
        try:
            prompt = (
                "你是内部知识库路由器。判断用户问题是否需要查询企业知识库，"
                "如果需要则输出 'RETRIEVE'，如果只是泛问、闲聊或不需要知识则输出 'ANSWER'。\n"
                f"问题：{question}"
            )
            response = self.router_model.invoke([HumanMessage(content=prompt)])
            result = str(response.content).strip().upper()
            return result if result in {"RETRIEVE", "ANSWER"} else "RETRIEVE"
        except Exception as exc:  # pragma: no cover - 边界保护
            logger.warning("Question routing failed: %s", exc)
            return "RETRIEVE"

    def generate_answer(self, question: str, context_docs: List[str], history: List[str]) -> str:
        """使用上下文和历史构造最终回答，强调以知识为主、回答简洁。"""
        if self.primary_model is None:
            return (
                "当前系统尚未配置 OpenAI API Key，无法直接调用大模型进行回答。"
                "请先在 .env 中配置真实的 OpenAI 凭据与 Milvus / 飞书连接信息后再试。"
            )

        context = "\n\n".join(f"- {doc}" for doc in context_docs[:5])
        history_text = "\n".join(f"{entry}" for entry in history[-4:])
        messages = [
            SystemMessage(
                content=(
                    "你是企业知识库专用助手。请先判断是否需要使用知识库工具查询信息；"
                    "如果问题涉及公司制度、流程、政策、文档、权限或内部知识，优先用工具获取事实依据。"
                    "利用工具返回的观察结果进行分析，最后再给出结构化结论。"
                    "如果知识不足，请明确说明未找到相关信息并给出建议。"
                )
            ),
            HumanMessage(
                content=(
                    f"历史对话：\n{history_text}\n\n"
                    f"用户问题：{question}\n\n"
                    f"参考资料：\n{context}\n\n"
                    "请遵循 ReAct 风格：先判断是否需要检索，再基于事实给出结论。"
                )
            ),
        ]
        response = self.primary_model.invoke(messages)
        return str(response.content).strip()
