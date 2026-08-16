"""Test questions for evaluating the SQL agent with RAGAS.

Each case pairs a question with the database it should be routed to, a short
reference answer used to judge the final report's correctness, and the tool
call sequence (agent/tools.py) the agent is expected to make. `reference_answer`
values are facts already verified directly against the database (see
agent/README.md usage examples) — keep them that way when adding cases,
rather than guessing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TestCase:
    question: str
    expected_database: str
    reference_answer: str
    expected_tools: tuple[str, ...]


TEST_CASES = [
    TestCase(
        question="Show me a bar chart of the top 8 movie genres by average rating, with at least 1000 ratings each",
        expected_database="movie_lens",
        reference_answer=(
            "The top 8 movie genres by average rating are: Film-Noir at 3.92, "
            "War at 3.79, Crime at 3.69, Documentary at 3.69, Drama at 3.68, "
            "Mystery at 3.67, Animation at 3.62, and Western at 3.60."
        ),
        expected_tools=("get_schema", "run_sql", "create_plot"),
    ),
    TestCase(
        question="Show me a bar chart of average order value by customer state, top 8 states",
        expected_database="olist",
        reference_answer=(
            "The top 8 states by average order value are: PB at 265.01, AC at "
            "242.84, AP at 239.16, AL at 234.13, RO at 233.03, PA at 224.38, "
            "TO at 219.91, and PI at 219.34."
        ),
        expected_tools=("get_schema", "run_sql", "create_plot"),
    ),
    TestCase(
        question="Show me a bar chart of the number of orders by payment type",
        expected_database="olist",
        reference_answer=(
            "The number of orders by payment type: credit card at 76,505, "
            "boleto at 19,784, voucher at 3,866, debit card at 1,528, and "
            "not_defined at 3."
        ),
        expected_tools=("get_schema", "run_sql", "create_plot"),
    ),
]
