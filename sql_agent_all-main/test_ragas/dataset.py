"""Test questions for evaluating the SQL agent with RAGAS.

Each case pairs a question with the database it should be routed to and a
short reference answer used to judge the final report's correctness.
`reference_answer` values are facts already verified directly against the
database (see agent/README.md usage examples) — keep them that way when
adding cases, rather than guessing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TestCase:
    question: str
    expected_database: str
    reference_answer: str


TEST_CASES = [
    TestCase(
        question="How many movies are in the movie_lens database?",
        expected_database="movie_lens",
        reference_answer="The movie_lens database contains 87,585 movies.",
    ),
    TestCase(
        question="How many movies are tagged with the tag 'sci-fi'?",
        expected_database="movie_lens",
        reference_answer="771 distinct movies are tagged 'sci-fi' in the movie_lens database.",
    ),
    TestCase(
        question="What are the top 5 highest-rated movies with at least 100 ratings?",
        expected_database="movie_lens",
        reference_answer=(
            "The top 5 highest-rated movies with at least 100 ratings are: "
            "Planet Earth II (2016) at 4.45, Planet Earth (2006) at 4.44, "
            "Band of Brothers (2001) at 4.43, Shawshank Redemption, The (1994) "
            "at 4.40, and Cosmos at 4.33."
        ),
    ),
    TestCase(
        question="How many products are in the olist database?",
        expected_database="olist",
        reference_answer="The olist database contains 32,951 products.",
    ),
    TestCase(
        question="How many distinct sellers are in the olist database?",
        expected_database="olist",
        reference_answer="The olist database has 3,095 distinct sellers.",
    ),
    TestCase(
        question="What is the most common payment method for orders?",
        expected_database="olist",
        reference_answer=(
            "Credit card is the most commonly used payment method for orders, "
            "used in 76,795 payments."
        ),
    ),
]
