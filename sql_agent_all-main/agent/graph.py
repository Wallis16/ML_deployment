from langgraph.graph import END, START, StateGraph

from .nodes import (
    create_plot,
    create_query,
    create_report,
    route_after_validation,
    run_query,
    validate_query,
)
from .state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("create_query", create_query)
    graph.add_node("validate_query", validate_query)
    graph.add_node("run_query", run_query)
    graph.add_node("create_report", create_report)
    graph.add_node("create_plot", create_plot)

    graph.add_edge(START, "create_query")
    graph.add_edge("create_query", "validate_query")
    graph.add_conditional_edges(
        "validate_query",
        route_after_validation,
        {"create_query": "create_query", "run_query": "run_query"},
    )
    graph.add_edge("run_query", "create_report")
    graph.add_edge("create_report", "create_plot")
    graph.add_edge("create_plot", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    png_bytes = app.get_graph().draw_mermaid_png()
    out_path = __file__.replace("graph.py", "graph.png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    print(f"Wrote {out_path}")
