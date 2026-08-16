# SQL agent

A LangGraph agent that answers a natural-language question by picking one of
the two Postgres databases (see [../docker](../docker)), then using SQL and
plotting tools to produce a short report plus an optional chart.

## Flow

```
route -> agent -> [tools -> agent]* -> finalize
```

- `route` — picks a database (`movie_lens` or `olist`) via a RAG lookup: the
  question is embedded locally with
  [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5)
  (`sentence-transformers`) and matched against pre-embedded copies of
  `../metadata/*_description.txt` stored in Postgres via `pgvector` (nearest
  neighbor by cosine distance — see [embeddings.py](embeddings.py)). No LLM
  call for this step, and it isn't re-made mid-run — a bad SQL query doesn't
  imply a bad database pick.
- `agent` — calls the LLM (Groq, via function-calling), given the chosen
  database and three tools (see [tools.py](tools.py)):
  - `get_schema` — returns `../schema_docs/*.txt` for the chosen database.
  - `run_sql` — rejects anything that isn't a single read-only `SELECT`/
    `WITH` statement, validates the rest against the live database with
    `EXPLAIN` (catches bad table/column names and syntax errors without
    executing anything), then runs it. Errors are returned to the model as
    the tool result so it can fix and retry.
  - `create_plot` — builds a chart from the most recent `run_sql` result and
    saves a PNG under `output/`; the model only calls this when a chart
    would add something beyond the text answer.
- `tools` — dispatches whatever `agent` asked for, then loops back to
  `agent` — up to a budget of `--max-attempts` (default 3) run_sql attempts
  plus room for schema/plot calls — before `finalize` reports the failure
  instead of inventing an answer.
- `finalize` — once the model responds with plain text instead of another
  tool call (or the budget runs out), extracts the report and the last
  query/result/plot for the caller.

See [graph.py](graph.py) for the graph definition — running
`python -m agent.graph` re-renders [graph.png](graph.png).

## Setup

```bash
uv venv                                          # creates .venv/ at the project root
uv pip install -r agent/requirements.txt --python .venv
source .venv/Scripts/activate                    # or .venv/bin/activate on macOS/Linux
```

Create `agent/.env` (git-ignored, not committed) with your Groq credentials:

```
GROQ_API_KEY=your-key-here   # https://console.groq.com
GROQ_MODEL=openai/gpt-oss-20b   # required — any Groq chat model id
```

Database credentials are read from [../docker/.env](../docker/.env) — the
container (`docker compose up -d` in `docker/`) must be running, on the
`pgvector/pgvector:pg16` image (see [../docker](../docker)) with an
`agent_metadata` database holding the routing embeddings.

Populate/refresh those embeddings (safe to re-run; only re-embeds a
description if its text changed):

```bash
python -m agent.embeddings
```

The embedding model (~130MB) downloads from Hugging Face on first run and is
cached locally after that.

## Usage

```bash
python -m agent.main "Which movie genres have the highest average rating?"
python -m agent.main "What's the average order value by customer state?"
```
