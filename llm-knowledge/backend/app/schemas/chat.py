from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色，例如 user、assistant、system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入的问题")
    conversation_id: Optional[str] = Field(default=None, description="会话 ID，用于保持上下文")
    history: List[ChatMessage] = Field(default_factory=list, description="历史消息列表")


class SourceDocument(BaseModel):
    title: str
    content: str
    source: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: List[SourceDocument] = Field(default_factory=list)
    confidence: float = 0.0
    cached: bool = False
    model_used: str = ""
