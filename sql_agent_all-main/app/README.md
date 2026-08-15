# API

FastAPI wrapper around the LangGraph agent in [../agent](../agent), for
deploying it as a service instead of running it via the CLI.

## Run

```bash
uv pip install -r ../agent/requirements.txt -r requirements.txt --python ../.venv
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

(run from the project root; requires `agent/.env` and a running
`docker/` database container — see [../agent/README.md](../agent/README.md))

Interactive docs at `http://localhost:8000/docs` once running.

## Endpoints

### `GET /health`

Liveness check.

### `POST /query`

```json
{
  "question": "What are the top 5 highest-rated movies with at least 100 ratings?",
  "max_attempts": 3
}
```

→

```json
{
  "database": "movie_lens",
  "sql": "SELECT ...",
  "report": "...",
  "plot_url": "/output/plot_20260810_120000.png",
  "error": null
}
```

`plot_url` is `null` when the agent decided the result wasn't worth
charting. `error` is populated (and `report` explains the failure in plain
language) if the query failed to execute. Generated chart PNGs are served
back under `/output/`.
