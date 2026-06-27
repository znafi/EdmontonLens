"""CityBot — a LangChain ReAct agent wrapping Gemini with warehouse SQL tools.

When ``GEMINI_API_KEY`` is configured, builds a real ReAct AgentExecutor backed
by ``ChatGoogleGenerativeAI`` (model from ``settings.gemini_model``). When it is
not configured (local dev / CI), falls back to a deterministic keyword router so
the /ask page and the API remain functional without external credentials.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, TypedDict

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import (
    BigQuerySQLTool,
    SchemaInspectorTool,
    run_sql,
)
from backend.config import settings

logger = logging.getLogger(__name__)


class AgentResult(TypedDict):
    answer: str
    sql_used: str
    rows: list[dict[str, Any]]


_executor: Any | None = None
_sql_tool: BigQuerySQLTool | None = None


def _build_executor() -> tuple[Any, BigQuerySQLTool]:
    """Construct the LangChain ReAct AgentExecutor (Gemini-backed)."""
    from langchain.agents import (  # type: ignore[attr-defined]
        AgentExecutor,
        create_react_agent,
    )
    from langchain_core.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0,
        timeout=30,
        max_retries=1,
    )
    sql_tool = BigQuerySQLTool()
    tools = [SchemaInspectorTool(), sql_tool]

    react_template = (
        SYSTEM_PROMPT
        + """

You have access to the following tools:

{tools}

Use this exact format:

Question: the input question you must answer
Thought: think about what to do
Action: the action to take, one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (Thought/Action/Action Input/Observation can repeat)
Thought: I now know the final answer
Final Answer: the plain-English answer, then a new line "SQL: <the SQL you ran>"

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    )
    prompt = PromptTemplate.from_template(react_template)
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=5,
        max_execution_time=45,
    )
    return executor, sql_tool


def _get_executor() -> tuple[Any, BigQuerySQLTool]:
    global _executor, _sql_tool
    if _executor is None or _sql_tool is None:
        _executor, _sql_tool = _build_executor()
    return _executor, _sql_tool


# Hard wall-clock ceiling for the whole agent run. If the LLM or a tool call
# stalls (e.g. a slow upstream), we abandon the agent and answer with the
# deterministic keyword router so the request never hangs.
_AGENT_DEADLINE_SECONDS = 50

# A shared pool we deliberately never block on shutting down. If a worker stalls
# on a hung upstream call, we abandon it (it leaks until the process recycles)
# and return a fallback rather than letting the HTTP request hang. Using a
# context manager here would defeat the timeout, because its __exit__ waits for
# the in-flight thread to finish.
_agent_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="citybot"
)


def _smalltalk_reply(question: str) -> str | None:
    """Return a friendly reply for greetings/small talk, else None.

    Without this, "hi" gets turned into a SQL query and a confusing table.
    """
    q = question.strip().lower().rstrip("!.? ")
    greetings = {
        "hi", "hello", "hey", "yo", "hiya", "howdy", "hi there", "hello there",
        "hey there", "good morning", "good afternoon", "good evening", "sup",
        "what's up", "whats up",
    }
    thanks = {"thanks", "thank you", "ty", "thx", "cheers", "appreciate it"}
    byes = {"bye", "goodbye", "see ya", "see you", "later"}
    if q in greetings:
        return (
            "Hi! I'm CityBot. Ask me about Edmonton's transit, parks, waste "
            "pickup, or neighbourhoods. For example: \"What day is garbage "
            "pickup in Glenora?\" or \"Which 5 stops have the worst delays?\""
        )
    if q in thanks:
        return "You're welcome! Ask me anything else about Edmonton's open data."
    if q in byes:
        return "Take care! Come back anytime you have a question about the city."
    return None


def answer_question(question: str) -> AgentResult:
    """Answer a natural-language question and return answer/SQL/rows."""
    chat = _smalltalk_reply(question)
    if chat is not None:
        return AgentResult(answer=chat, sql_used="", rows=[])

    if not settings.gemini_enabled:
        return _fallback_answer(question)

    future = _agent_pool.submit(_run_agent, question)
    try:
        return future.result(timeout=_AGENT_DEADLINE_SECONDS)
    except concurrent.futures.TimeoutError:
        future.cancel()
        logger.warning("Agent timed out after %ss, using fallback", _AGENT_DEADLINE_SECONDS)
        return _fallback_answer(question)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Agent error, using fallback: %s", exc)
        return _fallback_answer(question)


def _run_agent(question: str) -> AgentResult:
    """Answer via a direct Gemini text-to-SQL call (runs under a deadline).

    The LangChain ReAct executor (see ``_build_executor``) remains wired up, but
    the old ``langchain-google-genai`` client and the multi-step ReAct loop were
    unreliable in production: a single LLM call could stall past the request
    deadline. This path talks to the Gemini REST API directly in two quick
    steps — generate SQL, then summarise the rows — which is fast and robust.
    """
    sql = _generate_sql(question)
    df = run_sql(sql)
    rows = df.to_dict(orient="records")
    answer = _summarise_rows(question, rows)
    return AgentResult(answer=answer, sql_used=sql, rows=rows)


_GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def _gemini_call(prompt: str, timeout: float) -> str:
    """Call the Gemini REST API and return the first candidate's text.

    Retries once on a 429 (rate limit) after a short pause, since rapid
    successive questions can briefly exceed the per-minute quota.
    """
    import time

    import httpx

    url = _GEMINI_ENDPOINT.format(model=settings.gemini_model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2048},
    }
    for attempt in range(2):
        resp = httpx.post(
            url, params={"key": settings.gemini_api_key}, json=payload, timeout=timeout
        )
        if resp.status_code == 429 and attempt == 0:
            time.sleep(3)
            continue
        resp.raise_for_status()
        data = resp.json()
        return str(data["candidates"][0]["content"]["parts"][0]["text"]).strip()
    raise RuntimeError("Gemini rate limit (429) after retry")


def _generate_sql(question: str) -> str:
    """Ask Gemini for a single read-only SELECT that answers the question."""
    prompt = (
        SYSTEM_PROMPT
        + f"\n\nThe resident asked: \"{question}\"\n\n"
        "Write exactly ONE read-only SQL SELECT (SQLite/ANSI compatible) that "
        "answers it. Output ONLY the SQL with no explanation and no markdown "
        "code fences. Always include LIMIT 500 or fewer. For any text filter "
        "(neighbourhood names, waste types like garbage/recycling/organics, "
        "pickup days, etc.) match case-insensitively, e.g. "
        "LOWER(column) = LOWER('value') or column LIKE 'value', so values "
        "stored in a different case still match. Round decimal values to two "
        "places using ROUND(value, 2) in the SELECT."
    )
    raw = _gemini_call(prompt, timeout=25)
    return _clean_sql(raw)


def _clean_sql(raw: str) -> str:
    """Strip markdown fences / stray prose so we are left with a SELECT."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:3].lower() == "sql":
            text = text[3:]
    text = text.strip().rstrip(";")
    # If the model prepended prose, keep from the first SELECT/WITH onward.
    lowered = text.lower()
    for kw in ("select", "with"):
        idx = lowered.find(kw)
        if idx != -1:
            return text[idx:].strip()
    return text


def _summarise_rows(question: str, rows: list[dict[str, Any]]) -> str:
    """Ask Gemini for a short plain-English answer over the returned rows."""
    if not rows:
        return "I ran a query for that but it didn't return any matching data."
    import json

    sample = json.dumps(rows[:30], default=str)
    prompt = (
        f'A resident asked: "{question}"\n\n'
        f"A SQL query returned these rows as JSON:\n{sample}\n\n"
        "Answer the question in 1-3 short, friendly sentences based only on this "
        "data. Use specific numbers and names. Do not mention SQL, queries, or "
        "that you were given JSON."
    )
    try:
        return _gemini_call(prompt, timeout=20)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Summary call failed (%s); returning a basic answer", exc)
        return f"Here is what I found for your question ({len(rows)} results)."


def _split_answer_sql(text: str) -> tuple[str, str]:
    """Separate the plain-English answer from a trailing 'SQL:' block."""
    if "SQL:" in text:
        answer, _, sql = text.partition("SQL:")
        return answer.strip(), sql.strip()
    return text.strip(), ""


# --------------------------------------------------------------------------- #
# Deterministic fallback (no Gemini key required)
# --------------------------------------------------------------------------- #
_UNSURE_REPLY = (
    "I'm not sure I understood that. I can answer questions about Edmonton's "
    "transit delays, parks, waste pickup schedules, and neighbourhood stats. "
    "Try asking something like \"What day is recycling in Highlands?\" or "
    "\"Which 5 stops have the worst delays?\""
)


def _fallback_answer(question: str) -> AgentResult:
    """Keyword-routed canned queries for when the LLM is unavailable.

    Only answers when the question clearly matches a known topic. Anything
    unrecognised (off-topic or gibberish) gets a friendly nudge instead of a
    random data dump, so CityBot behaves like a chatbot rather than a table.
    """
    q = question.lower()
    sql: str | None = None
    if "garbage" in q or "pickup" in q or "waste" in q or "recycl" in q or "organic" in q:
        sql = (
            "SELECT n.neighbourhood_name, w.waste_type, w.pickup_day "
            "FROM waste_schedules w "
            "JOIN neighbourhoods n ON n.neighbourhood_id = w.neighbourhood_id "
            "LIMIT 50"
        )
    elif "park" in q:
        sql = (
            "SELECT n.neighbourhood_name, COUNT(*) AS park_count "
            "FROM parks p JOIN neighbourhoods n "
            "ON n.neighbourhood_id = p.neighbourhood_id "
            "GROUP BY n.neighbourhood_name ORDER BY park_count DESC LIMIT 10"
        )
    elif "stop" in q and "delay" in q:
        sql = (
            "SELECT stop_id, AVG(avg_delay_mins) AS mean_delay "
            "FROM transit_stop_delays GROUP BY stop_id "
            "ORDER BY mean_delay DESC LIMIT 5"
        )
    elif "delay" in q or "route" in q or "bus" in q or "transit" in q:
        sql = (
            "SELECT route_id, SUM(delayed_trips) AS total_delays "
            "FROM transit_performance GROUP BY route_id "
            "ORDER BY total_delays DESC LIMIT 10"
        )
    elif "neighbourhood" in q or "neighborhood" in q or "score" in q or "best" in q:
        sql = (
            "SELECT n.neighbourhood_name, k.overall_score "
            "FROM neighbourhood_kpis k "
            "JOIN neighbourhoods n ON n.neighbourhood_id = k.neighbourhood_id "
            "ORDER BY k.overall_score DESC LIMIT 10"
        )

    if sql is None:
        return AgentResult(answer=_UNSURE_REPLY, sql_used="", rows=[])

    try:
        df = run_sql(sql)
        rows = df.to_dict(orient="records")
        if not rows:
            return AgentResult(answer=_UNSURE_REPLY, sql_used="", rows=[])
        answer = (
            "Here is what I found in the EdmontonLens warehouse "
            f"(showing {len(rows)} rows)."
        )
        return AgentResult(answer=answer, sql_used=sql, rows=rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallback query failed: %s", exc)
        return AgentResult(
            answer=(
                "I'm having trouble reaching the data right now. Please try "
                "again in a moment."
            ),
            sql_used="",
            rows=[],
        )
