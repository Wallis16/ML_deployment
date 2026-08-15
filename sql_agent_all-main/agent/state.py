from typing import Any, Optional

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """State threaded through the graph: create_query -> validate_query
    -> (loop back to create_query while invalid) -> run_query -> create_report
    -> create_plot.
    """

    question: str

    database: str
    query: str
    attempt: int
    max_attempts: int
    is_valid: bool
    validation_error: Optional[str]

    columns: list[str]
    rows: list[dict[str, Any]]
    run_error: Optional[str]

    report: str
    plot_path: Optional[str]
