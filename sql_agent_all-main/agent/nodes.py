"""The five nodes in the graph: create_query -> validate_query -> (loop back
while invalid) -> run_query -> create_report -> create_plot."""

import re
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import db
from .docs import get_schema_reference
from .embeddings import select_database
from .llm import call_llm, call_llm_structured
from .state import AgentState

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


# ---------------------------------------------------------------------------
# 1. Create query
# ---------------------------------------------------------------------------

CREATE_QUERY_SYSTEM = """You are a PostgreSQL expert. Given a user's question and a \
database schema reference, write a single read-only SQL query that answers the \
question.

Rules:
- Only use tables and columns that exist in the provided schema reference.
- Write a single SELECT statement (a WITH ... SELECT CTE is fine). Never write \
INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or GRANT.
- Prefer explicit column lists over SELECT *.
- Add a LIMIT when the question doesn't imply an aggregate or single-row answer, to \
keep the result set small.
"""

QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "sql": {
            "type": "string",
            "description": "A single read-only PostgreSQL SELECT statement, no trailing semicolon.",
        },
    },
    "required": ["sql"],
    "additionalProperties": False,
}


def create_query(state: AgentState) -> dict:
    attempt = state.get("attempt", 0)

    # Database routing happens once, via a local embedding model + pgvector
    # nearest-neighbor lookup (see embeddings.py) — not an LLM call, and not
    # re-decided on retries, since a bad SQL query doesn't imply a bad database
    # pick.
    database = state.get("database") if attempt > 0 else select_database(state["question"])[0]

    parts = [
        f"Question: {state['question']}",
        "",
        f"Schema reference for {database}:",
        get_schema_reference(database),
    ]

    if attempt > 0 and state.get("query"):
        parts += [
            "",
            "Your previous attempt failed validation. Fix the query.",
            f"Previous SQL:\n{state['query']}",
            f"Validation error:\n{state.get('validation_error')}",
        ]

    result = call_llm_structured(CREATE_QUERY_SYSTEM, "\n".join(parts), QUERY_SCHEMA, schema_name="sql_query")

    return {
        "database": database,
        "query": result["sql"],
        "attempt": attempt + 1,
    }


# ---------------------------------------------------------------------------
# 2. Validate query
# ---------------------------------------------------------------------------

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|COPY)\b",
    re.IGNORECASE,
)


def validate_query(state: AgentState) -> dict:
    sql = state["query"].strip().rstrip(";")

    if not re.match(r"^\s*(WITH|SELECT)\b", sql, re.IGNORECASE):
        return {
            "is_valid": False,
            "validation_error": "Query must start with SELECT or WITH — only read-only queries are allowed.",
        }
    if _FORBIDDEN.search(sql):
        return {
            "is_valid": False,
            "validation_error": "Query contains a disallowed write/DDL statement.",
        }

    try:
        db.explain_query(state["database"], sql)
    except Exception as exc:  # bad table/column name, syntax error, etc.
        return {"is_valid": False, "validation_error": str(exc), "query": sql}

    return {"is_valid": True, "validation_error": None, "query": sql}


def route_after_validation(state: AgentState) -> str:
    if state.get("is_valid"):
        return "run_query"
    if state.get("attempt", 0) >= state.get("max_attempts", 3):
        # Out of retries — proceed anyway so run_query/create_report can
        # surface the failure to the user instead of the graph silently dying.
        return "run_query"
    return "create_query"


# ---------------------------------------------------------------------------
# 3. Run query
# ---------------------------------------------------------------------------


def run_query(state: AgentState) -> dict:
    try:
        df = db.run_query(state["database"], state["query"])
    except Exception as exc:
        return {"columns": [], "rows": [], "run_error": str(exc)}

    return {
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
        "run_error": None,
    }


# ---------------------------------------------------------------------------
# 4. Create report
# ---------------------------------------------------------------------------

REPORT_SYSTEM = """You write short, clear analytical reports for a business \
audience based on SQL query results. Be factual — only state what the data shows. \
Lead with the direct answer to the question, including the specific numbers/names \
the data shows. Do not add commentary about the query, table names, or how the \
number was derived (e.g. never say things like "this was calculated using a COUNT \
query"), and skip headers, bold labels, or other formatting for short answers — a \
plain sentence or two is enough. If the question implies a list (e.g. "top N"), \
report every item in it, not just the first. If the query failed, explain plainly \
that the question could not be answered and why, without inventing data."""


def create_report(state: AgentState) -> dict:
    if state.get("run_error"):
        prompt = (
            f"Question: {state['question']}\n"
            f"Database: {state.get('database')}\n"
            f"SQL:\n{state.get('query')}\n\n"
            f"The query failed to execute with this error:\n{state['run_error']}\n\n"
            "Write a short report explaining that the question could not be answered."
        )
    else:
        rows = state.get("rows", [])
        prompt = (
            f"Question: {state['question']}\n"
            f"Database: {state['database']}\n"
            f"SQL:\n{state['query']}\n\n"
            f"Result: {len(rows)} row(s), columns: {state.get('columns')}\n"
            f"Sample rows (up to 20): {rows[:20]}\n\n"
            "Write a concise report (a few sentences to a short paragraph) answering "
            "the question based on this data."
        )

    report = call_llm(REPORT_SYSTEM, prompt, max_tokens=1024)
    return {"report": report}


# ---------------------------------------------------------------------------
# 5. Create plot
# ---------------------------------------------------------------------------

PLOT_SYSTEM = """You decide whether a SQL result set is worth visualizing and, if \
so, which columns and chart type to use. Only choose columns that are present in the \
result. Set should_plot to false if the result has fewer than 2 rows, has no numeric \
column, or a chart wouldn't add anything beyond the report."""

PLOT_SCHEMA = {
    "type": "object",
    "properties": {
        "should_plot": {"type": "boolean"},
        "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "hist"]},
        "x": {"type": "string"},
        "y": {"type": "string"},
        "title": {"type": "string"},
    },
    "required": ["should_plot", "chart_type", "x", "y", "title"],
    "additionalProperties": False,
}


def create_plot(state: AgentState) -> dict:
    rows = state.get("rows") or []
    columns = state.get("columns") or []
    if state.get("run_error") or len(rows) < 2 or not columns:
        return {"plot_path": None}

    prompt = (
        f"Question: {state['question']}\n"
        f"Columns: {columns}\n"
        f"Sample rows (up to 10): {rows[:10]}\n"
    )
    spec = call_llm_structured(PLOT_SYSTEM, prompt, PLOT_SCHEMA, schema_name="plot_spec", max_tokens=512)

    if not spec.get("should_plot") or spec.get("x") not in columns or spec.get("y") not in columns:
        return {"plot_path": None}

    df = pd.DataFrame(rows, columns=columns)
    x, y, chart_type, title = spec["x"], spec["y"], spec["chart_type"], spec["title"]

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

    return {"plot_path": str(path)}
