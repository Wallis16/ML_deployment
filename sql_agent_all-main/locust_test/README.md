# Load testing

Locust load test for the SQL agent API ([../app](../app)), to see whether
the `/query` endpoint holds up under concurrent traffic — and where it
breaks first if it doesn't.

See [LOAD_TEST_REPORT.md](LOAD_TEST_REPORT.md) for a full write-up of a
scalability run — latency by concurrency, the Groq rate-limit ceilings hit,
and conclusions on whether/how this scales.

⚠️ **This is not a synthetic benchmark.** Every simulated `/query` request
runs the real LangGraph agent: a Groq call to write SQL, a live `EXPLAIN`
against Postgres, the query itself, a Groq call for the report, and usually
a Groq call to decide on a chart. Load testing this means real Groq usage
and real load on your Postgres container — start with a small `--users`
count, especially if you're on a Groq free tier with tight rate limits.

## Setup

```bash
uv pip install -r requirements.txt --python ../.venv
```

Requires the API ([../app](../app)) running and reachable, and the
database container ([../docker](../docker)) up.

## Run

```bash
./run_load_test.sh                    # 5 users, spawn rate 1, 1 minute
./run_load_test.sh 20 5 2m            # 20 users, spawn rate 5, 2 minutes
HOST=https://your-deployed-api ./run_load_test.sh 10 2 1m
```

Writes `results/<timestamp>/`:
- **`summary.txt`** — request counts, failure rate, throughput, and
  min/median/avg/p95/p99/max response times, aggregated and per endpoint
- **`summary.png`** — two charts: requests/s + failures/s + concurrent
  users over time, and response time percentiles (p50/p95/p99) over time
- **`report.html`** — Locust's own interactive report
- `stats_*.csv` — the raw Locust output the above are generated from

## Reading the results

- **`/query` response times are dominated by Groq round-trips and the live
  `EXPLAIN`/query against Postgres** — typically single-digit seconds per
  request even with no load.
- **`app/main.py`'s `/query` handler is a sync `def`**, so FastAPI runs it
  in a thread pool (default ~40 threads) rather than blocking the event
  loop — the thread pool itself is not the limiting factor at any
  realistic concurrency here.
- **Measured bottleneck: Groq's tokens-per-minute (TPM) limit, not
  Postgres or FastAPI.** A run with just 5 concurrent users produced
  `groq.RateLimitError: 429 ... tokens per minute (TPM): Limit 8000` —
  each `/query` makes 2-3 Groq calls (write SQL, write the report,
  decide on a chart), so TPM gets exhausted fast on the free/on_demand
  tier. Response times also degraded sharply (p50 ~1.2s at 3 users →
  p50 ~31s, p99 ~35s at 5 users) as requests queued behind the limit. If
  you see `HTTP 500` failures, check the API's logs (`app/main.py` now
  logs the full traceback via `logger.exception` for exactly this reason)
  before assuming it's a DB or FastAPI problem.
- **Failures worth distinguishing**: HTTP-level failures (non-200, timeout)
  vs `error` in the JSON body (the agent ran but the query failed, e.g. a
  Postgres connection error) — `locustfile.py` marks both as Locust
  failures via `catch_response`, but `summary.txt`'s failure list and
  `report.html` show which is which. A `500` from a Groq rate limit and a
  `200` with a Postgres `error` in the body are different bottlenecks —
  don't conflate them.

## Rerun the chart/summary without rerunning the test

```bash
python summarize.py results/<timestamp>
```
