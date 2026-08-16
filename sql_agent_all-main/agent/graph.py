"""LangGraph orchestration for the tool-calling agent: `agent` calls the LLM
(given the three tools in tools.py) and `tools` dispatches whatever it asked
for, looping until the model responds with no further tool call — the
standard LangGraph ReAct-style shape.

    route -> agent -> [tools -> agent]* -> finalize

Database routing (`route`) happens once, up front, via a local embedding
model + pgvector nearest-neighbor lookup (see embeddings.py) — not an LLM
call, and not something the model can second-guess mid-run. `tools` always
runs whatever `agent` asks for; the `max_attempts` budget only bounds how
many more times the loop is allowed to go back to `agent` afterward — if the
budget runs out mid-loop, `finalize` reports the failure instead of
inventing an answer.
"""

import json
import operator
from typing import Annotated, Any, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .embeddings import select_database
from .llm import call_llm_tools
from .tools import TOOL_SCHEMAS, make_tools

AGENT_SYSTEM = """You are a PostgreSQL analyst agent answering a natural-language \
question over the '{database}' database.

You have three tools:
- get_schema — returns the table/column schema reference for this database. Call \
this first; never guess table or column names.
- run_sql — validates and executes a single read-only SQL statement and returns the \
result. If it errors, or the result doesn't look right, fix the query and call it \
again.
- create_plot — saves a chart from the most recent run_sql result, if a chart would \
meaningfully add to the answer.

Rules:
- Always call run_sql to get the actual data before answering, even if you recognize \
the question and already believe you know the answer — these are public datasets and \
your training data is not a substitute for querying the live database.
- Only use tables/columns that get_schema actually returned.
- Write a single SELECT statement (a WITH ... SELECT CTE is fine). Never write \
INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or GRANT.
- Prefer explicit column lists over SELECT *, and add a LIMIT unless the question \
implies an aggregate or single-row answer.
- Only call create_plot if the result has at least 2 rows and a numeric column, and \
a chart would add something beyond the text answer — most questions don't need one.
- Once you have your final answer, respond in plain text with no further tool call: \
a short, factual report. Lead with the direct answer, including the specific \
numbers/names the data shows. Don't mention the query, table names, or how the \
number was derived. Skip headers, bold labels, or other formatting for short \
answers — a plain sentence or two is enough. If the question implies a list (e.g. \
"top N"), report every item in it, not just the first. If run_sql keeps failing, \
explain plainly that the question could not be answered and why, without inventing \
data."""


class AgentState(TypedDict, total=False):
    question: str
    max_attempts: int

    database: str
    session: dict[str, Any]  # mutable run_sql/create_plot state — see tools.make_tools
    rounds: int

    messages: Annotated[list[dict[str, Any]], operator.add]
    tool_calls: Annotated[list[dict[str, Any]], operator.add]

    query: Optional[str]
    columns: list[str]
    rows: list[dict[str, Any]]
    run_error: Optional[str]
    report: str
    plot_path: Optional[str]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def route(state: AgentState) -> dict:
    database, _ = select_database(state["question"])
    session: dict[str, Any] = {
        "query": None,
        "columns": [],
        "rows": [],
        "run_error": None,
        "plot_path": None,
        "df": None,
    }
    return {
        "database": database,
        "session": session,
        "rounds": 0,
        "messages": [
            {"role": "system", "content": AGENT_SYSTEM.format(database=database)},
            {"role": "user", "content": state["question"]},
        ],
    }


def call_model(state: AgentState) -> dict:
    message = call_llm_tools(state["messages"], TOOL_SCHEMAS)

    assistant_message: dict[str, Any] = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        assistant_message["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
            }
            for tool_call in message.tool_calls
        ]

    return {"messages": [assistant_message], "rounds": state.get("rounds", 0) + 1}


def call_tools(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    tools = make_tools(state["database"], state["session"])

    tool_messages = []
    log = []
    for tool_call in last_message.get("tool_calls") or []:
        name = tool_call["function"]["name"]
        try:
            args = json.loads(tool_call["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}

        handler = tools.get(name)
        result = handler(args) if handler else f"Error: unknown tool {name!r}"
        log.append({"name": name, "args": args})
        tool_messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": result})

    return {"messages": tool_messages, "tool_calls": log}


def finalize(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    session = state["session"]

    if last_message.get("role") == "assistant" and not last_message.get("tool_calls"):
        report = last_message.get("content") or "(no report produced)"
    else:
        report = "I couldn't answer this question within the allotted number of attempts."
        if session.get("run_error"):
            report += f" Last error: {session['run_error']}"

    return {
        "report": report,
        "query": session["query"],
        "columns": session["columns"],
        "rows": session["rows"],
        "run_error": session["run_error"],
        "plot_path": session["plot_path"],
    }


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


def route_after_agent(state: AgentState) -> str:
    last_message = state["messages"][-1]
    return "tools" if last_message.get("tool_calls") else "finalize"


def route_after_tools(state: AgentState) -> str:
    # Budget: a get_schema call, `max_attempts` run_sql attempts, an optional
    # create_plot call, and the final no-tool-call turn.
    max_rounds = state.get("max_attempts", 3) + 3
    return "finalize" if state.get("rounds", 0) >= max_rounds else "agent"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("route", route)
    graph.add_node("agent", call_model)
    graph.add_node("tools", call_tools)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "route")
    graph.add_edge("route", "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "finalize": "finalize"})
    graph.add_conditional_edges("tools", route_after_tools, {"agent": "agent", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    png_bytes = app.get_graph().draw_mermaid_png()
    out_path = __file__.replace("graph.py", "graph.png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    print(f"Wrote {out_path}")
