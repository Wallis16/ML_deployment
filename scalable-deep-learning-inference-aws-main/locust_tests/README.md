# Locust Latency Tests

This folder contains a Locust test for measuring latency of the `POST /generate`
endpoint.

The test always sends the same payload:

```json
{
  "prompt": "Explain AWS ECS in one sentence.",
  "max_new_tokens": 100,
  "temperature": 0.7
}
```

## Run With UI

Start the API first:

```powershell
$env:SMOLLM_MOCK = "1"
uvicorn app.main:app --reload
```

Use mock mode only to verify the load test locally. For real latency numbers,
run the API with the model loaded or point `--host` at the deployed service.

Then run Locust:

```powershell
locust -f locust_tests/locustfile.py --host http://localhost:8000
```

Open `http://localhost:8089`, choose the number of users and spawn rate, and
watch the latency percentiles for `POST /generate`.

## Run Headless

```powershell
locust -f locust_tests/locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 -t 2m
```

Useful columns in the output are average latency, median latency, p95, p99, and
failure count.


P1
GENERATE_PROMPT = "Who is Ronaldo?"
GENERATE_TEMPERATURE = 0
MAX_NEW_TOKENS = 100