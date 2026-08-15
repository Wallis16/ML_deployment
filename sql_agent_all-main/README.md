# sql-agent

A LangGraph agent that turns a natural-language question into SQL, runs it
against one of two Postgres databases, and returns a plain-language report
plus an optional chart — with an API, a UI, load tests, and a RAGAS eval
suite around it.

## How it works

1. **Route** — the question is embedded locally
   ([`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5))
   and matched by nearest neighbor (`pgvector`) against the two database
   descriptions, to pick `movie_lens` or `olist` without an LLM call.
2. **Write + validate SQL** — the LLM (Groq) writes a `SELECT` against the
   chosen database's schema reference; it's validated with `EXPLAIN` against
   the live database and retried (with the error fed back) if invalid.
3. **Run** — the validated query executes against Postgres.
4. **Report + plot** — the result is summarized in plain language, and
   charted if the model decides it's worth charting.

See [agent/README.md](agent/README.md) for the full graph and node-by-node
breakdown.

## Project layout

| Path | What it is |
| --- | --- |
| [agent/](agent/README.md) | The LangGraph agent (routing, SQL generation, validation, reporting, plotting) — runnable as a CLI |
| [docker/](docker/README.md) | Postgres container: `movie_lens`, `olist`, and `agent_metadata` (routing embeddings) |
| [app/](app/README.md) | FastAPI wrapper exposing the agent as an HTTP service |
| [ui/](ui/README.md) | Streamlit front end, talks to `app/` over HTTP |
| [locust_test/](locust_test/README.md) | Load testing the API, with report/summary generation |
| [test_ragas/](test_ragas/test_agent.py) | RAGAS-based eval suite: database routing accuracy, tool-call accuracy, and answer correctness |
| `raw_data/`, `metadata/`, `schema_docs/` | Source CSVs (downloaded, not checked in — see [Data sources](#data-sources)) and the reference text the agent/router read from |

## Data sources

`raw_data/` isn't included in the repo — download it first:

- **MovieLens** → [ml-32m.zip](https://files.grouplens.org/datasets/movielens/ml-32m.zip)
  (from [grouplens.org/datasets/movielens](https://grouplens.org/datasets/movielens/)).
  Unzip so `movies.csv`, `ratings.csv`, `tags.csv`, and `links.csv` end up
  directly under `raw_data/movie_lens/`.
- **Olist** → [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
  (Kaggle — free account required). Unzip so the `olist_*_dataset.csv`
  files and `product_category_name_translation.csv` end up directly under
  `raw_data/olist/`.

`docker/load/*.sql` (run by `load_data.sh` below) `COPY`s from those exact
paths, so filenames and folder placement need to match.

## Quick start

```bash
# 1. database
cd docker
docker compose up -d
./load_data.sh
cd ..

# 2. environment (from the project root)
uv venv
uv pip install -r agent/requirements.txt --python .venv
source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
# create agent/.env with GROQ_API_KEY and GROQ_MODEL — see agent/README.md
python -m agent.embeddings      # populate the routing embeddings (one-time)

# 3. run it
python -m agent.main "Which movie genres have the highest average rating?"
```

That's the agent as a one-off CLI call. To run it as a service with a web
UI instead, keep going:

```bash
# 4. install the API + UI's own deps into the same venv
uv pip install -r app/requirements.txt -r ui/requirements.txt --python .venv

# 5. start the API (terminal 1, venv activated, from the project root)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 6. start the UI (terminal 2, venv activated, from the project root)
streamlit run ui/app.py
```

Then open `http://localhost:8501`, type a question, hit **Ask**. The API
alone is at `http://localhost:8000` (interactive docs at `/docs`) if you
want to call `POST /query` directly instead of through the UI. Both need
step 1-3 done first (database up, `agent/.env` set, embeddings populated).
Details/troubleshooting: [app/README.md](app/README.md),
[ui/README.md](ui/README.md).

## Evaluating and load testing

- `pytest test_ragas/ -v -s` — scores routing accuracy, tool-call accuracy,
  and final-report correctness (see [test_ragas/test_agent.py](test_ragas/test_agent.py))
- `locust_test/run_load_test.sh` — load tests the `/query` endpoint; see
  [locust_test/README.md](locust_test/README.md) for how to read the results
  (Groq's TPM limit, not Postgres or FastAPI, is the measured bottleneck)
