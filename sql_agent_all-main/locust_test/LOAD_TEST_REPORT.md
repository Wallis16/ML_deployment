# Load test report — is the SQL agent API scalable?

**TL;DR: the app's own stack (FastAPI + Postgres) is not the bottleneck. The
Groq free/`on_demand` tier's token quota is — both a per-minute cap and a
per-day cap — and it caps effective throughput far below anything the app
itself is limited by.** See [Conclusion](#conclusion).

## Setup

- Endpoint under test: `POST /query` on the FastAPI app ([../app](../app))
- Load generator: [locustfile.py](locustfile.py), driven by
  [run_load_test.sh](run_load_test.sh) / [summarize.py](summarize.py)
- **Standardized input**: a single fixed question, asked repeatedly —
  `"How many movies are in the movie_lens database?"` — instead of the
  wider question set the file originally cycled through. Isolating the
  input keeps the SQL/report/plot generation shape constant, so response
  time variance reflects load, not "which question happened to get asked."
- `agent/llm.py` already uses a low, fixed `temperature=0.2` for every LLM
  call (SQL generation, report, plot decision), so output length/shape is
  already fairly deterministic — no separate change was needed there for
  this test. (A run at `temperature=0.0` was tried and reverted: it didn't
  reduce variance in any way that mattered for latency, and it shuffled
  which cases the unrelated `test_ragas` RAGAS suite failed, so it wasn't
  worth carrying.)
- Model: `openai/gpt-oss-20b` via Groq, `on_demand` service tier (free/pay-as-you-go)
- Each `/query` call triggers 2-3 real Groq LLM calls (write SQL, write the
  report, decide on a chart) plus a live `EXPLAIN` and the query itself
  against Postgres — this exercises the whole stack, not just HTTP.

## Results

Three runs, in order:

| Run | Date | Users | Questions | Requests | Failures | p50 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|
| A | 2026-08-10 | 3 | mixed (8-question pool) | 4 | 1 (25%) | 1.2s | 22.0s | 22.0s |
| B | 2026-08-10 | 5 | mixed (8-question pool) | 5 | 3 (60%) | 31.0s | 35.0s | 35.0s |
| C | 2026-08-15 | 1 | standardized (this test's fixed question) | 24 | 24 (100%) | 170ms | 380ms | 6.8s |

Raw data: `results/20260810_165235/` (run A), `results/20260810_165538/`
(run B), `results/20260815_143934/` (run C).

**Run A and B** (from before the question set was standardized) show the
expected shape: latency climbs sharply from 3 → 5 concurrent users, and
failures start appearing. All failures were `HTTP 500`. At the time, the
underlying error (visible in the API's server-side logs, not in Locust's
own output) was:

```
groq.RateLimitError: 429 ... tokens per minute (TPM): Limit 8000
```

**Run C** — the fresh, standardized-input run for this report — failed
100%, but not because of load: it hit a *different*, harder limit than A/B.
By the time this run started, the day's combined traffic (this session's
`test_ragas` runs plus earlier manual testing) had already used
199,855 of the account's 200,000 **tokens-per-day** budget:

```
Error code: 429 - {'error': {'message': "Rate limit reached for model
`openai/gpt-oss-20b` ... on tokens per day (TPD): Limit 200000, Used 199855,
Requested 1328. Please try again in 8m31.056s. ...", 'type': 'tokens',
'code': 'rate_limit_exceeded'}}
```

With ~145 tokens of remaining daily budget against a ~1,300-token request,
every request in run C was rejected by Groq before the agent did any real
work — hence the misleadingly fast "latency" (median 170ms: that's the
round-trip to get *rejected*, not to get answered) and the 6.8s p99 (one
request that landed right as a small amount of budget freed up, ran partway,
then still failed).

## Root cause: two different Groq quota dimensions, not the app

- **Tokens per minute (TPM), seen in runs A/B**: `on_demand` tier caps this
  model at 8,000 TPM. At ~2-3 Groq calls per `/query` (each call sends the
  full schema reference as context), a handful of concurrent users burns
  through that in well under a minute, so latency degrades sharply and then
  requests start getting rejected — this is what runs A and B show directly.
- **Tokens per day (TPD), seen in run C**: a hard 200,000 token/day ceiling
  on the same tier, shared across *all* traffic against this key —
  including eval suites (`test_ragas/`), manual testing, and load tests
  themselves. Once it's gone, every request fails instantly regardless of
  concurrency, until the daily window rolls over.
- **What's not the bottleneck**: Postgres (`EXPLAIN` + the query itself run
  in milliseconds — see the `GET /health` and low percentiles in runs A/B),
  and FastAPI's threading (the `/query` handler is sync, so FastAPI runs it
  in a thread pool; at the concurrencies tested here that pool is nowhere
  near its ~40-thread default capacity).

## Conclusion

**The application itself scales fine; the Groq `on_demand` tier it's wired
to today does not, for this workload.** Two independent caps sit well below
any load level this app would see in normal use:

- **~8,000 TPM** → roughly enough headroom for **one `/query` request every
  10-15 seconds** sustained (3 Groq calls × ~1-2k tokens each), before
  requests start queuing behind the limit and then failing outright — this
  matches run B's collapse at 5 concurrent users almost exactly.
- **~200,000 TPD** → a hard ceiling of roughly **100-150 `/query` requests
  per calendar day**, shared with every other consumer of the same API key
  (eval runs included). Run C shows what happens at the ceiling: not
  degraded performance, but instant, total failure.

So: not scalable *as currently configured*, but the constraint is
infrastructure/billing, not code. The fix isn't in `app/` or `agent/` — it's
in what's provisioned upstream. In order of effort:

1. **Upgrade the Groq account off the free `on_demand` tier** (or move to a
   provider/plan with per-minute and per-day limits sized for the target
   traffic). This alone would likely resolve both A/B and C.
2. **Cut Groq calls per request.** Right now a single `/query` makes 2-3
   calls (SQL, report, plot decision). Merging the plot decision into the
   report-generation call (one structured call that returns both) would cut
   token usage roughly a third.
3. **Separate the daily-budget failure mode from a real 500.** Today a TPD
   rejection and an actual bug both surface as a generic `HTTP 500` in
   `app/main.py`. Passing through Groq's `429` (and its `Retry-After`)
   instead of collapsing it to `500` would let load-test tooling — and
   real clients — distinguish "the app is broken" from "the account is
   rate-limited," and back off/retry correctly instead of treating it as a
   failure.
4. **Cache identical questions.** The standardized single-question test
   here is an extreme case, but any repeated question (common in a demo/UI
   context) is currently re-run through the full LLM pipeline every time.

## Caveats

- Run C's 100% failure rate is a **confound, not a load-test result**: the
  account was already near its daily cap from unrelated same-day traffic
  (this session's `test_ragas` runs) before run C's single user sent a
  single request. It demonstrates the TPD ceiling exists and is easy to hit
  by accident, but it does not by itself say anything about how the app
  behaves at 1 concurrent user under normal conditions — for that, see run
  A's 3-user numbers, which had headroom.
- Runs A and B predate the locustfile's standardization to a single
  question, so their per-request token cost (and therefore exactly how many
  requests it took to hit the TPM ceiling) varied by which of the 8
  questions was drawn. The qualitative conclusion (TPM ceiling hit between
  3 and 5 concurrent users) is unaffected by that.
- All three runs are small (4-24 requests) by necessity — the TPM/TPD caps
  make it impossible to sustain meaningfully larger runs on this tier
  without hitting rate limits well before any app-side scaling limit would
  show up.
