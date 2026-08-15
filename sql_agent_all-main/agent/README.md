# SQL agent

A LangGraph agent that answers a natural-language question by picking one of
the two Postgres databases (see [../docker](../docker)), writing and
validating SQL against it, running it, and producing a short report plus an
optional chart.

## Flow

```
create_query -> validate_query -> run_query -> create_report -> create_plot
                     ^   |
                     └───┘ (loop back to create_query while the query is invalid)
```

- `create_query` — picks a database (`movie_lens` or `olist`) via a RAG
  lookup: the question is embedded locally with
  [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5)
  (`sentence-transformers`) and matched against pre-embedded copies of
  `../metadata/*_description.txt` stored in Postgres via `pgvector`
  (nearest neighbor by cosine distance — see [embeddings.py](embeddings.py)).
  No LLM call for this step, and the choice isn't re-made on retries (a bad
  SQL query doesn't imply a bad database pick). It then writes a SQL query
  using `../schema_docs/*.txt` as the column/table reference.
- `validate_query` — rejects non-`SELECT` statements outright, then validates
  the query against the live database with `EXPLAIN` (catches bad table/column
  names and syntax errors without executing anything). On failure, loops back
  to `create_query` with the error so it can retry — up to `--max-attempts`
  (default 3).
- `run_query` — executes the validated query and captures the result set.
- `create_report` — summarizes the result (or explains the failure) in plain
  language.
- `create_plot` — asks the model whether the result is worth charting and
  with which columns; saves a PNG under `output/` if so.

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
