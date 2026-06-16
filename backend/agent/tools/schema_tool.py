"""LangChain tool that returns the schema for a requested table."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from backend.agent.prompts import TABLE_SCHEMAS


def describe_table(table_name: str) -> str:
    """Return a human-readable column listing for ``table_name``."""
    key = table_name.strip().strip("`").lower()
    schema = TABLE_SCHEMAS.get(key)
    if schema is None:
        available = ", ".join(TABLE_SCHEMAS.keys())
        return f"Unknown table '{table_name}'. Available tables: {available}."
    lines = [f"Schema for `{key}`:"]
    for col, desc in schema.items():
        lines.append(f"  - {col}: {desc}")
    return "\n".join(lines)


class SchemaInspectorTool(BaseTool):
    """Tool: returns the full schema for any table name the agent asks about."""

    name: str = "SchemaInspectorTool"
    description: str = (
        "Return the column names and types for a warehouse table. Input is a "
        "single table name (e.g. 'transit_performance'). ALWAYS call this before "
        "writing SQL against a table."
    )

    def _run(self, table_name: str) -> str:  # type: ignore[override]
        return describe_table(table_name)

    async def _arun(self, table_name: str) -> str:  # type: ignore[override]
        return describe_table(table_name)
