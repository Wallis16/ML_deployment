# SmolLM ECS Inference

GPU-ready FastAPI service for running `HuggingFaceTB/SmolLM2-360M-Instruct`
locally before deploying it to AWS ECS.

## API

- `GET /health` returns `{"status":"healthy"}`
- `POST /generate` generates text from a prompt
- `GET /metrics` exposes Prometheus metrics

Example:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is AWS ECS?"}'
```

Response:

```json
{
  "response": "AWS ECS is a managed container orchestration service...",
  "latency_ms": 245,
  "tokens_generated": 30,
  "tokens_per_second": 122.4,
  "first_token_latency_ms": 245
}
```

## Local Development

Install `uv`, then create and use a local virtual environment:

```powershell
uv venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

Run the API in mock mode for fast local endpoint checks:

```powershell
$env:SMOLLM_MOCK = "1"
uvicorn app.main:app --reload
```

Run tests:

```powershell
$env:SMOLLM_MOCK = "1"
pytest -q
```

`SMOLLM_MOCK=1` starts the API without downloading or loading the model, which is
useful for tests and endpoint checks.

## GPU Docker Run

Create `.env` from `.env.example`, then build and run:

```bash
docker build -f docker/Dockerfile -t smollm-api .
docker run --gpus all --env-file .env -p 8000:8000 smollm-api
```

Docker Compose:

```bash
docker compose up --build
```

The container uses `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` and installs
`torch==2.6.0` without the duplicate pip-managed CUDA packages. Docker installs
only runtime dependencies from `requirements-prod.txt`; `pytest`, `locust`, and
benchmark-only packages stay in `requirements.txt` for local development. The
host still needs the NVIDIA driver and NVIDIA Container Toolkit installed.

## Baseline Metrics

Capture these before ECS deployment:

| Metric | Where to collect |
| --- | --- |
| Model load time | `model_load_time_seconds` metric |
| First token latency | `first_token_latency_ms` response field |
| End-to-end latency | `latency_ms` response field or `generation_latency_seconds` |
| Tokens/sec | `tokens_per_second` response field and metric |
| GPU memory usage | `gpu_memory_allocated_bytes`, `gpu_memory_reserved_bytes` |
| GPU utilization | `nvidia-smi` during benchmark |

Run the included benchmark:

```powershell
python scripts/benchmark.py --url http://localhost:8000 --requests 10
```
