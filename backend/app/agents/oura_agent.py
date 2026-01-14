"""LangGraph-powered Oura agent with data tools."""

from __future__ import annotations

import json
import operator
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Annotated, Literal, TypedDict
from urllib.parse import urlparse

import httpx
from langchain.tools import tool
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from ..storage import repo
from ..storage.models import OuraRawEvent
from ..core.config import get_settings
from .base import Agent, AgentContext, AgentResult, ChatMessage

SYSTEM_PROMPT = (
    "You are Oura Coach, a non-medical wellness assistant. "
    "Use the available tools to answer questions about the user's Oura data. "
    "You can suggest experiments and general wellness guidance, but you must not "
    "diagnose, treat, or claim clinical certainty. "
    "If asked for medical advice, recommend consulting a qualified professional."
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    llm_calls: int


@dataclass
class DateRange:
    start: date
    end: date


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


def _extract_resolved_range(tool_output: str | None) -> dict | None:
    if not tool_output:
        return None
    try:
        payload = json.loads(tool_output)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    if "days" in payload:
        return {"days": payload.get("days")}

    if "start_date" in payload and "end_date" in payload:
        return {
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
        }

    return None


def _extract_tool_calls(messages: list[BaseMessage]) -> list[dict]:
    tool_results: dict[str, str] = {}
    for message in messages:
        if isinstance(message, ToolMessage):
            tool_results[message.tool_call_id] = message.content

    calls: list[dict] = []
    for message in messages:
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for tool_call in tool_calls:
            call_id = tool_call.get("id")
            call = {
                "name": tool_call.get("name", ""),
                "args": tool_call.get("args", {}) or {},
            }
            resolved_range = _extract_resolved_range(tool_results.get(call_id))
            if resolved_range:
                call["resolved_range"] = resolved_range
            calls.append(call)

    return calls


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _resolve_date_range(
    days: int | None,
    start_date: str | None,
    end_date: str | None,
) -> tuple[DateRange | None, dict | None, str | None]:
    if days is not None and (start_date or end_date):
        return None, None, "Provide either days OR a start/end date range, not both."

    if days is not None:
        if days <= 0:
            return None, None, "Days must be a positive integer."
        end = date.today()
        start = end - timedelta(days=days)
        return DateRange(start=start, end=end), {"days": days}, None

    if not start_date and not end_date:
        default_days = 14
        end = date.today()
        start = end - timedelta(days=default_days)
        return DateRange(start=start, end=end), {"days": default_days}, None

    if not start_date or not end_date:
        return None, None, "Provide both start_date and end_date in YYYY-MM-DD format."

    try:
        start = _parse_date(start_date)
        end = _parse_date(end_date)
    except ValueError:
        return None, None, "Dates must be in YYYY-MM-DD format."

    if start > end:
        return None, None, "start_date must be before or equal to end_date."

    return (
        DateRange(start=start, end=end),
        {"start_date": start.isoformat(), "end_date": end.isoformat()},
        None,
    )


def _serialize_events(events: list[OuraRawEvent]) -> list[dict]:
    items: list[dict] = []
    for event in events:
        try:
            items.append(json.loads(event.payload))
        except json.JSONDecodeError:
            continue
    return items


def _clamp_limit(limit: int, maximum: int = 500) -> int:
    if limit < 1:
        return 1
    if limit > maximum:
        return maximum
    return limit


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _make_oura_tools(db, user_id: str):
    @tool
    def get_readiness_data(
        days: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 120,
    ) -> str:
        """Fetch Oura daily readiness data.

        Provide either days (lookback) or a start/end date range in YYYY-MM-DD.
        """
        limit_value = _clamp_limit(limit)
        date_range, range_info, error = _resolve_date_range(days, start_date, end_date)
        if error:
            return json.dumps({"error": error})

        events = repo.get_raw_events_by_range(
            db,
            user_id,
            "daily_readiness",
            date_range.start.isoformat(),
            date_range.end.isoformat(),
            limit=limit_value,
        )

        items = _serialize_events(events)
        return json.dumps({
            "endpoint": "daily_readiness",
            "count": len(items),
            **(range_info or {}),
            "items": items,
        })

    @tool
    def get_sleep_data(
        days: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 120,
    ) -> str:
        """Fetch Oura daily sleep data.

        Provide either days (lookback) or a start/end date range in YYYY-MM-DD.
        """
        limit_value = _clamp_limit(limit)
        date_range, range_info, error = _resolve_date_range(days, start_date, end_date)
        if error:
            return json.dumps({"error": error})

        events = repo.get_raw_events_by_range(
            db,
            user_id,
            "daily_sleep",
            date_range.start.isoformat(),
            date_range.end.isoformat(),
            limit=limit_value,
        )

        items = _serialize_events(events)
        return json.dumps({
            "endpoint": "daily_sleep",
            "count": len(items),
            **(range_info or {}),
            "items": items,
        })

    @tool
    def get_activity_data(
        days: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 120,
    ) -> str:
        """Fetch Oura daily activity data.

        Provide either days (lookback) or a start/end date range in YYYY-MM-DD.
        """
        limit_value = _clamp_limit(limit)
        date_range, range_info, error = _resolve_date_range(days, start_date, end_date)
        if error:
            return json.dumps({"error": error})

        events = repo.get_raw_events_by_range(
            db,
            user_id,
            "daily_activity",
            date_range.start.isoformat(),
            date_range.end.isoformat(),
            limit=limit_value,
        )

        items = _serialize_events(events)
        return json.dumps({
            "endpoint": "daily_activity",
            "count": len(items),
            **(range_info or {}),
            "items": items,
        })

    @tool
    def web_fetch(url: str, max_chars: int = 4000) -> str:
        """Fetch and extract text from a public web page URL."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return json.dumps({"error": "Only http/https URLs are supported."})

        try:
            response = httpx.get(
                url,
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "OuraCoachBot/1.0"},
            )
        except httpx.RequestError as exc:
            return json.dumps({"error": f"Request failed: {exc}"})

        if response.status_code >= 400:
            return json.dumps({
                "error": f"HTTP {response.status_code}",
                "url": url,
            })

        text = ""
        try:
            import trafilatura

            text = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
            ) or ""
        except Exception:
            text = ""

        if not text:
            text = _strip_html(response.text)
        text = text[: max_chars or 4000]
        return json.dumps({
            "url": str(response.url),
            "content": text,
        })

    @tool
    def web_search(query: str, max_results: int = 5) -> str:
        """Search the web for relevant sources and return top results."""
        limit = _clamp_limit(max_results, maximum=10)
        try:
            from duckduckgo_search import DDGS
        except Exception:
            return json.dumps({"error": "Search dependency is not available."})

        results: list[dict] = []
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=limit):
                results.append({
                    "title": result.get("title"),
                    "url": result.get("href"),
                    "snippet": result.get("body"),
                })

        return json.dumps({"query": query, "results": results})

    return [
        get_readiness_data,
        get_sleep_data,
        get_activity_data,
        web_search,
        web_fetch,
    ]


def _build_graph(model: ChatOpenAI, tools_by_name: dict[str, object]):
    async def llm_call(state: AgentState) -> dict:
        response = await model.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        )
        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    def tool_node(state: AgentState) -> dict:
        results: list[ToolMessage] = []
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", None)
        if not tool_calls:
            return {"messages": []}

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_instance = tools_by_name.get(tool_name)
            if tool_instance is None:
                results.append(
                    ToolMessage(
                        content=json.dumps({"error": "Unknown tool"}),
                        tool_call_id=tool_call.get("id", ""),
                    )
                )
                continue

            observation = tool_instance.invoke(tool_call.get("args", {}))
            if not isinstance(observation, str):
                observation = json.dumps(observation)
            results.append(
                ToolMessage(content=observation, tool_call_id=tool_call.get("id", ""))
            )

        return {"messages": results}

    def should_continue(state: AgentState) -> Literal["tool_node", END]:
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tool_node"
        return END

    builder = StateGraph(AgentState)
    builder.add_node("llm_call", llm_call)
    builder.add_node("tool_node", tool_node)
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    builder.add_edge("tool_node", "llm_call")
    return builder.compile()


class OuraAgent(Agent):
    name = "oura_agent"
    depends_on: list[str] = []

    def __init__(self, db, user_id: str, model: str = "gpt-4o-mini", temperature: float = 0.3):
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

        tools = _make_oura_tools(db, user_id)
        tools_by_name = {tool_instance.name: tool_instance for tool_instance in tools}
        model_with_tools = ChatOpenAI(model=model, temperature=temperature).bind_tools(tools)

        self._graph = _build_graph(model_with_tools, tools_by_name)

    async def run(self, ctx: AgentContext) -> AgentResult:
        messages = _format_history(ctx.history)
        messages.append(HumanMessage(content=ctx.message))

        result = await self._graph.ainvoke({"messages": messages, "llm_calls": 0})
        reply = _extract_reply(result["messages"])
        tool_calls = _extract_tool_calls(result["messages"])

        return AgentResult(
            payload={"reply": reply, "tool_calls": tool_calls},
            confidence=0.4,
        )
