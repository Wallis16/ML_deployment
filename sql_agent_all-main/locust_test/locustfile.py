"""Locust load test for the SQL agent API (see ../app).

Every simulated /query request triggers a real LangGraph run: a Groq LLM
call to write SQL, a live EXPLAIN against Postgres, the query itself, a
Groq call for the report, and usually a Groq call to decide on a chart —
so this is exercising the whole stack, not just the HTTP layer. Keep
--users modest; this isn't free traffic.

Run via ../run_load_test.sh, or directly:
    locust -f locustfile.py --host http://localhost:8000
"""

import random

from locust import HttpUser, between, task

# QUESTIONS = [
#     "How many movies are in the movie_lens database?",
#     "What are the top 5 highest-rated movies with at least 100 ratings?",
#     "What tags are most commonly applied to movies?",
#     "Which movie genres have the highest average rating?",
#     "How many distinct sellers are in the olist database?",
#     "What is the most common payment method for orders?",
#     "Which product categories have the most orders?",
#     "What's the average order value by customer state?",
# ]

QUESTIONS = [
    "How many movies are in the movie_lens database?"
]


class SqlAgentUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def query(self):
        question = random.choice(QUESTIONS)
        with self.client.post(
            "/query",
            json={"question": question, "max_attempts": 3},
            name="/query",
            timeout=120,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            data = response.json()
            if data.get("error"):
                response.failure(f"agent error: {data['error'][:200]}")
