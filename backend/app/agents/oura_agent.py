"""LangGraph-powered Oura agent with data tools."""

from __future__ import annotations

import asyncio
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


def _coerce_tool_call(tool_call: object) -> dict:
    if isinstance(tool_call, dict):
        return {
            "id": tool_call.get("id", ""),
            "name": tool_call.get("name", ""),
            "args": tool_call.get("args", {}) or {},
        }
    return {
        "id": getattr(tool_call, "id", ""),
        "name": getattr(tool_call, "name", ""),
        "args": getattr(tool_call, "args", {}) or {},
    }


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


def _format_pubmed_date(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        return parsed.strftime("%Y/%m/%d")
    except ValueError:
        return None


async def _pubmed_request(
    url: str,
    params: dict,
    max_retries: int = 4,
    base_delay: float = 0.5,
) -> tuple[dict | None, str | None]:
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url, params=params, timeout=12.0)
            except httpx.RequestError:
                response = None

            if response is None:
                pass
            elif response.status_code == 429 or response.status_code >= 500:
                pass
            elif response.status_code >= 400:
                return None, f"PubMed API error: HTTP {response.status_code}"
            else:
                try:
                    return response.json(), None
                except ValueError:
                    pass

            if attempt < max_retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))

    return None, "PubMed API is cooling down, try again later."


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
    def create_experiment(
        title: str,
        objective: str,
        hypothesis: str,
        protocol: str,
        duration_days: int,
        success_criteria: str,
        start_date: str | None = None,
        metrics: list[str] | None = None,
    ) -> str:
        """Create a new wellness experiment for the user."""
        if duration_days <= 0:
            return json.dumps({"error": "duration_days must be a positive integer."})

        if start_date:
            try:
                start = _parse_date(start_date)
            except ValueError:
                return json.dumps({"error": "start_date must be in YYYY-MM-DD format."})
        else:
            start = date.today()

        end = start + timedelta(days=duration_days)
        metrics_payload = json.dumps(metrics) if metrics else None

        experiment = repo.create_experiment(
            db,
            user_id,
            title=title,
            objective=objective,
            hypothesis=hypothesis,
            protocol=protocol,
            duration_days=duration_days,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            success_criteria=success_criteria,
            metrics=metrics_payload,
        )

        return json.dumps({
            "experiment_id": experiment.id,
            "title": experiment.title,
            "objective": experiment.objective,
            "hypothesis": experiment.hypothesis,
            "protocol": experiment.protocol,
            "duration_days": experiment.duration_days,
            "start_date": experiment.start_date,
            "end_date": experiment.end_date,
            "success_criteria": experiment.success_criteria,
            "metrics": metrics or [],
            "status": experiment.status,
        })

    @tool
    async def web_fetch(url: str, max_chars: int = 4000) -> str:
        """Fetch and extract text from a public web page URL."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return json.dumps({"error": "Only http/https URLs are supported."})

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
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
            from ddgs import DDGS
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

    @tool
    async def pubmed_search(
        query: str,
        max_results: int = 5,
        sort: str | None = "relevance",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """Search PubMed and return the top results for a query."""
        if not query.strip():
            return json.dumps({"error": "Query is required."})

        limit = _clamp_limit(max_results, maximum=20)
        params: dict[str, str | int] = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": limit,
        }

        if sort:
            params["sort"] = sort

        if start_date or end_date:
            if not start_date or not end_date:
                return json.dumps({"error": "Provide both start_date and end_date (YYYY-MM-DD)."})
            formatted_start = _format_pubmed_date(start_date)
            formatted_end = _format_pubmed_date(end_date)
            if not formatted_start or not formatted_end:
                return json.dumps({"error": "Dates must be in YYYY-MM-DD format."})
            params["mindate"] = formatted_start
            params["maxdate"] = formatted_end
            params["datetype"] = "pdat"

        api_key = os.getenv("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key
        email = os.getenv("NCBI_EMAIL")
        if email:
            params["email"] = email
        params["tool"] = os.getenv("NCBI_TOOL", "oura_agent")

        search_data, error = await _pubmed_request(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params,
        )
        if error:
            return json.dumps({"error": error})

        esearch = (search_data or {}).get("esearchresult", {})
        id_list = esearch.get("idlist", [])
        total_count = esearch.get("count", "0")

        if not id_list:
            return json.dumps({
                "query": query,
                "count": int(total_count) if str(total_count).isdigit() else 0,
                "results": [],
            })

        summary_params: dict[str, str | int] = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        if api_key:
            summary_params["api_key"] = api_key
        if email:
            summary_params["email"] = email
        summary_params["tool"] = params["tool"]

        summary_data, summary_error = await _pubmed_request(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            summary_params,
        )
        if summary_error:
            return json.dumps({"error": summary_error})

        result_block = (summary_data or {}).get("result", {})
        uids = result_block.get("uids", id_list)
        results: list[dict] = []

        for uid in uids:
            record = result_block.get(uid, {})
            if not record:
                continue
            article_ids = record.get("articleids", [])
            doi = next(
                (item.get("value") for item in article_ids if item.get("idtype") == "doi"),
                None,
            )
            pmc = next(
                (item.get("value") for item in article_ids if item.get("idtype") == "pmc"),
                None,
            )
            authors = [author.get("name") for author in record.get("authors", []) if author.get("name")]
            results.append({
                "pmid": uid,
                "title": record.get("title"),
                "journal": record.get("fulljournalname") or record.get("source"),
                "pubdate": record.get("pubdate"),
                "authors": authors,
                "volume": record.get("volume"),
                "issue": record.get("issue"),
                "pages": record.get("pages"),
                "doi": doi,
                "pmc": pmc,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            })

        return json.dumps({
            "query": query,
            "count": int(total_count) if str(total_count).isdigit() else None,
            "results": results,
        })

    return [
        get_readiness_data,
        get_sleep_data,
        get_activity_data,
        create_experiment,
        web_search,
        pubmed_search,
        web_fetch,
    ]


def _build_graph(model: ChatOpenAI, tools_by_name: dict[str, object], system_prompt: str):
    async def llm_call(state: AgentState) -> dict:
        response = await model.ainvoke(
            [SystemMessage(content=system_prompt)] + state["messages"]
        )
        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    async def tool_node(state: AgentState) -> dict:
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

            observation = await tool_instance.ainvoke(tool_call.get("args", {}))
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

    def __init__(
        self,
        db,
        user_id: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        system_prompt: str | None = None,
        extra_tools: list[object] | None = None,
    ):
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

        tools = _make_oura_tools(db, user_id)
        if extra_tools:
            tools.extend(extra_tools)
        tools_by_name = {tool_instance.name: tool_instance for tool_instance in tools}
        model_with_tools = ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=True,
        ).bind_tools(tools)

        prompt = system_prompt or SYSTEM_PROMPT
        self._graph = _build_graph(model_with_tools, tools_by_name, prompt)

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

    async def stream(self, ctx: AgentContext):
        messages = _format_history(ctx.history)
        messages.append(HumanMessage(content=ctx.message))

        tool_results: dict[str, str] = {}
        tool_calls_raw: list[dict] = []
        reply_parts: list[str] = []
        fallback_reply = ""

        try:
            async for event in self._graph.astream_events(
                {"messages": messages, "llm_calls": 0},
                version="v1",
            ):
                event_type = event.get("event")
                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is None:
                        continue
                    text = getattr(chunk, "content", None)
                    if text:
                        reply_parts.append(text)
                        yield {"type": "token", "content": text}
                    continue

                if event_type != "on_chain_end":
                    continue

                name = event.get("name")
                output = event.get("data", {}).get("output")
                if not isinstance(output, dict):
                    continue

                if name == "tool_node":
                    for message in output.get("messages", []):
                        if isinstance(message, ToolMessage):
                            tool_results[message.tool_call_id] = message.content
                            resolved_range = _extract_resolved_range(message.content)
                            payload = {
                                "type": "tool_end",
                                "tool_call_id": message.tool_call_id,
                            }
                            if resolved_range:
                                payload["resolved_range"] = resolved_range
                            yield payload
                    continue

                if name != "llm_call":
                    continue

                for message in output.get("messages", []):
                    if not isinstance(message, AIMessage):
                        continue
                    if message.tool_calls:
                        for call in message.tool_calls:
                            call_payload = _coerce_tool_call(call)
                            tool_calls_raw.append(call_payload)
                            yield {
                                "type": "tool_start",
                                "tool_call": {
                                    "id": call_payload.get("id", ""),
                                    "name": call_payload.get("name", ""),
                                    "args": call_payload.get("args", {}) or {},
                                },
                            }
                        continue
                    if message.content:
                        fallback_reply = _extract_reply([message])
        except Exception:
            yield {
                "type": "error",
                "message": "Failed to reach Oura Coach. Please try again.",
            }
            return

        reply = "".join(reply_parts).strip() or fallback_reply
        if not reply:
            reply = "Sorry, I did not get a response. Please try again."

        tool_calls: list[dict] = []
        for call in tool_calls_raw:
            resolved_range = _extract_resolved_range(tool_results.get(call.get("id", "")))
            payload = {
                "name": call.get("name", ""),
                "args": call.get("args", {}) or {},
            }
            if resolved_range:
                payload["resolved_range"] = resolved_range
            tool_calls.append(payload)

        yield {"type": "done", "reply": reply, "tool_calls": tool_calls}
