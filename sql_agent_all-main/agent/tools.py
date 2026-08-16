"""The three tools the agent can call: get_schema, run_sql, create_plot.

Each tool is backed by plain Python/SQL, not another LLM call — the model
only decides when to call them and with what arguments. `make_tools` closes
over the question's database and a shared `session` dict so run_sql's result
is available to create_plot without the model having to round-trip the data
through its own context.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import db
from .docs import get_schema_reference

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|COPY)\b",
    re.IGNORECASE,
)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": (
                "Returns the table/column schema reference for this question's database. "
                "Call this before writing any SQL — never guess table or column names."
            ),
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Validates and executes a single read-only SQL statement against the database "
                "and returns the resulting rows. Returns an error message instead of results if "
                "the query is invalid, unsafe, or fails to execute — fix the query and call this "
                "again."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A single read-only SELECT (or WITH ... SELECT) statement, no trailing semicolon.",
                    },
                },
                "required": ["sql"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_plot",
            "description": (
                "Saves a chart image built from the most recent successful run_sql result "
                "(call run_sql first — this errors otherwise). Only call this when a chart would "
                "meaningfully add to the answer, e.g. a ranked or trended result with 2+ rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "hist"]},
                    "x": {
                        "type": "string",
                        "description": "Column name from the last run_sql result to use for the x-axis.",
                    },
                    "y": {
                        "type": "string",
                        "description": "Column name from the last run_sql result to use for the y-axis.",
                    },
                    "title": {"type": "string"},
                },
                "required": ["chart_type", "x", "y", "title"],
                "additionalProperties": False,
            },
        },
    },
]


def make_tools(database: str, session: dict[str, Any]) -> dict[str, Callable[[dict[str, Any]], str]]:
    """Builds the tool-name -> executor mapping for one agent run. Executors
    mutate `session` (query/columns/rows/run_error/plot_path/df) so the
    caller can read back the final state once the loop ends."""

    def get_schema(_args: dict[str, Any]) -> str:
        return get_schema_reference(database)

    def run_sql(args: dict[str, Any]) -> str:
        sql = str(args.get("sql", "")).strip().rstrip(";")

        if not re.match(r"^\s*(WITH|SELECT)\b", sql, re.IGNORECASE):
            return "Error: query must start with SELECT or WITH — only read-only queries are allowed."
        if _FORBIDDEN.search(sql):
            return "Error: query contains a disallowed write/DDL statement."

        try:
            db.explain_query(database, sql)
            df = db.run_query(database, sql)
        except Exception as exc:  # bad table/column name, syntax error, etc.
            session["run_error"] = str(exc)
            return f"Error: {exc}"

        session["query"] = sql
        session["columns"] = list(df.columns)
        session["rows"] = df.to_dict(orient="records")
        session["run_error"] = None
        session["df"] = df

        return json.dumps(
            {
                "row_count": len(df),
                "columns": list(df.columns),
                "sample_rows": df.head(20).to_dict(orient="records"),
            },
            default=str,
        )

    def create_plot(args: dict[str, Any]) -> str:
        df = session.get("df")
        if df is None:
            return "Error: no query results yet — call run_sql first."

        x, y, chart_type = args.get("x"), args.get("y"), args.get("chart_type")
        title = args.get("title") or ""
        if x not in df.columns or y not in df.columns:
            return f"Error: {x!r} or {y!r} is not a column in the last result ({list(df.columns)})."
        if chart_type not in ("bar", "line", "scatter", "hist"):
            return f"Error: unknown chart_type {chart_type!r} — use bar, line, scatter, or hist."

        fig, ax = plt.subplots(figsize=(9, 6))
        if chart_type == "bar":
            labels = df[x].astype(str)
            ax.bar(labels, df[y])
            if labels.str.len().max() > 10 or len(df) > 8:
                plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        elif chart_type == "line":
            ax.plot(df[x], df[y], marker="o")
        elif chart_type == "scatter":
            ax.scatter(df[x], df[y])
        elif chart_type == "hist":
            ax.hist(df[y])
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        fig.tight_layout()

        OUTPUT_DIR.mkdir(exist_ok=True)
        path = OUTPUT_DIR / f"plot_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        session["plot_path"] = str(path)

        return f"Chart saved to {path.name}."

    return {"get_schema": get_schema, "run_sql": run_sql, "create_plot": create_plot}
