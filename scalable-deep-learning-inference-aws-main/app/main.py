import time

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from app import metrics
from app.model import generator
from app.schemas import (
    DeviceStatusResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
)

app = FastAPI(
    title="SmolLM ECS Inference API",
    version="0.1.0",
    description="GPU-ready FastAPI inference service for SmolLM2-360M-Instruct.",
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@app.get("/device", response_model=DeviceStatusResponse)
def device_status() -> DeviceStatusResponse:
    """Return the current inference device and visible CUDA GPUs."""
    return generator.device_status()


@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest) -> GenerateResponse:
    metrics.GENERATE_REQUESTS.inc()
    started = time.perf_counter()

    try:
        result = generator.generate(
            prompt=payload.prompt,
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
        )
    except Exception as exc:
        metrics.GENERATE_FAILURES.inc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    elapsed_seconds = time.perf_counter() - started
    latency_ms = int(elapsed_seconds * 1000)
    tokens_per_second = (
        result.tokens_generated / elapsed_seconds if elapsed_seconds > 0 else 0.0
    )

    metrics.GENERATION_LATENCY.observe(elapsed_seconds)
    metrics.TOKENS_GENERATED.inc(result.tokens_generated)
    metrics.TOKENS_PER_SECOND.set(tokens_per_second)
    metrics.update_gpu_metrics()

    return GenerateResponse(
        response=result.text,
        latency_ms=latency_ms,
        tokens_generated=result.tokens_generated,
        tokens_per_second=round(tokens_per_second, 2),
        first_token_latency_ms=result.first_token_latency_ms,
    )
