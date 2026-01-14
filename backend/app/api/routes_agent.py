"""Agent routes for chat interactions."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from ..agents import AgentContext, ChatMessage, OuraAgent
from ..storage.models import User
from ..storage.db import get_db
from .deps import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatMessagePayload(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessagePayload] = Field(default_factory=list)


class ToolCallPayload(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)
    resolved_range: dict | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallPayload] = Field(default_factory=list)


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        agent = OuraAgent(db=db, user_id=user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    history = [ChatMessage(role=item.role, content=item.content) for item in request.history]
    result = await agent.run(
        AgentContext(user_id=user.id, message=request.message, history=history, db=db)
    )
    payload = result.payload if isinstance(result.payload, dict) else {}
    reply = payload.get("reply", "")
    tool_calls = payload.get("tool_calls", []) or []
    return ChatResponse(reply=reply, tool_calls=tool_calls)
