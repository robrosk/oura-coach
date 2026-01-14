"""LangGraph-backed chat agent."""

from __future__ import annotations

import operator
import os
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from ..core.config import get_settings
from .base import Agent, AgentContext, AgentResult, ChatMessage

SYSTEM_PROMPT = (
    "You are Oura Coach, a non-medical wellness assistant. "
    "You can suggest experiments and general wellness guidance, but you must not "
    "diagnose, treat, or claim clinical certainty. "
    "If asked for medical advice, recommend consulting a qualified professional."
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    llm_calls: int


def _format_history(history: list[ChatMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in history:
        content = item.content.strip()
        if not content:
            continue
        if item.role == "user":
            messages.append(HumanMessage(content=content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _extract_reply(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(str(part["text"]))
                return " ".join(parts).strip()
            return str(content)
    return ""


def _build_graph(model: ChatOpenAI):
    async def llm_call(state: AgentState) -> dict:
        response = await model.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        )
        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    builder = StateGraph(AgentState)
    builder.add_node("llm_call", llm_call)
    builder.add_edge(START, "llm_call")
    builder.add_edge("llm_call", END)
    return builder.compile()


class OpenAIChatAgent(Agent):
    name = "openai_chat"
    depends_on: list[str] = []

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4):
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        self._model = ChatOpenAI(model=model, temperature=temperature)
        self._graph = _build_graph(self._model)

    async def run(self, ctx: AgentContext) -> AgentResult:
        messages = _format_history(ctx.history)
        messages.append(HumanMessage(content=ctx.message))

        result = await self._graph.ainvoke(
            {"messages": messages, "llm_calls": 0}
        )
        reply = _extract_reply(result["messages"])

        return AgentResult(
            payload={"reply": reply},
            confidence=0.4,
        )
