"""Base agent abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class AgentContext:
    user_id: str
    message: str
    history: list[ChatMessage] = field(default_factory=list)
    db: Any | None = None


@dataclass
class AgentResult:
    payload: Any
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Agent(ABC):
    name: str = "agent"
    depends_on: list[str] = []

    @abstractmethod
    async def run(self, ctx: AgentContext) -> AgentResult:
        raise NotImplementedError
