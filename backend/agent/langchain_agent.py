"""CityBot — a LangChain ReAct agent wrapping Gemini with warehouse SQL tools.

When ``GEMINI_API_KEY`` is configured, builds a real ReAct AgentExecutor backed
by ``ChatGoogleGenerativeAI`` (gemini-1.5-pro). When it is not configured (local
dev / CI), falls back to a deterministic keyword router so the /ask page and the
API remain functional without external credentials.
"""

from __future__ import annotations

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


def answer_question(question: str) -> AgentResult:
    """Answer a natural-language question and return answer/SQL/rows."""
    if not settings.gemini_enabled:
        return _fallback_answer(question)

    try:
        executor, sql_tool = _get_executor()
        result = executor.invoke({"input": question})
        output = str(result.get("output", "")).strip()
        answer, sql_used = _split_answer_sql(output)
        return AgentResult(
            answer=answer or output,
            sql_used=sql_used or sql_tool.last_sql,
            rows=sql_tool.last_rows,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Agent error, using fallback: %s", exc)
        return _fallback_answer(question)


def _split_answer_sql(text: str) -> tuple[str, str]:
    """Separate the plain-English answer from a trailing 'SQL:' block."""
    if "SQL:" in text:
        answer, _, sql = text.partition("SQL:")
        return answer.strip(), sql.strip()
    return text.strip(), ""


# --------------------------------------------------------------------------- #
# Deterministic fallback (no Gemini key required)
# --------------------------------------------------------------------------- #
def _fallback_answer(question: str) -> AgentResult:
    """Keyword-routed canned queries so dev works without an LLM."""
    q = question.lower()
    try:
        if "garbage" in q or "pickup" in q or "waste" in q:
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
        elif "delay" in q or "route" in q:
            sql = (
                "SELECT route_id, SUM(delayed_trips) AS total_delays "
                "FROM transit_performance GROUP BY route_id "
                "ORDER BY total_delays DESC LIMIT 10"
            )
        else:
            sql = (
                "SELECT neighbourhood_id, overall_score "
                "FROM neighbourhood_kpis ORDER BY overall_score DESC LIMIT 10"
            )
        df = run_sql(sql)
        rows = df.to_dict(orient="records")
        answer = (
            "Here is what I found based on the EdmontonLens warehouse "
            f"(showing {len(rows)} rows). Note: running in offline mode without "
            "Gemini, so this used a templated query."
        )
        return AgentResult(answer=answer, sql_used=sql, rows=rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fallback query failed: %s", exc)
        return AgentResult(
            answer=(
                "I couldn't reach the data warehouse. Make sure the ETL pipeline "
                "has run (python -m backend.etl.pipeline) and try again."
            ),
            sql_used="",
            rows=[],
        )
