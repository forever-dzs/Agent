from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, SourceDocument
from app.services.knowledge_agent import KnowledgeAgentService

router = APIRouter(prefix="/chat", tags=["chat"])
agent = KnowledgeAgentService()


@router.post("/query", response_model=ChatResponse)
async def query_chat(request: ChatRequest) -> ChatResponse:
    """核心问答接口：将用户输入送入 LangGraph 检索链路。"""
    try:
        conversation_id = request.conversation_id or str(uuid.uuid4())
        history = [f"{message.role}: {message.content}" for message in request.history]
        result = agent.query(request.message, history, conversation_id)

        sources = [
            SourceDocument(
                title=item.get("title", "unknown"),
                content=item.get("content", ""),
                source=item.get("source", ""),
                score=float(item.get("score", 0.0) or 0.0),
                metadata=item.get("metadata", {}),
            )
            for item in result.get("sources", [])
        ]

        return ChatResponse(
            answer=result.get("answer", ""),
            conversation_id=conversation_id,
            sources=sources,
            confidence=0.9 if sources else 0.4,
            cached=bool(result.get("cached", False)),
            model_used=result.get("model_used", ""),
        )
    except Exception as exc:  # pragma: no cover - 输出统一错误
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {exc}") from exc


@router.get("/health")
async def chat_health() -> dict:
    return {"status": "ok", "service": "chat-engine"}
