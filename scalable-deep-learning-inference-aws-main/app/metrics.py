from prometheus_client import Counter, Gauge, Histogram

GENERATE_REQUESTS = Counter(
    "generate_requests_total",
    "Total text generation requests.",
)

GENERATE_FAILURES = Counter(
    "generate_failures_total",
    "Total failed text generation requests.",
)

GENERATION_LATENCY = Histogram(
    "generation_latency_seconds",
    "End-to-end text generation latency.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)

TOKENS_GENERATED = Counter(
    "tokens_generated_total",
    "Total generated tokens returned by the model.",
)

TOKENS_PER_SECOND = Gauge(
    "tokens_per_second",
    "Tokens generated per second for the latest request.",
)

MODEL_LOAD_TIME = Gauge(
    "model_load_time_seconds",
    "Model load time in seconds.",
)

GPU_MEMORY_ALLOCATED = Gauge(
    "gpu_memory_allocated_bytes",
    "CUDA memory allocated by PyTorch.",
)

GPU_MEMORY_RESERVED = Gauge(
    "gpu_memory_reserved_bytes",
    "CUDA memory reserved by PyTorch.",
)


def update_gpu_metrics() -> None:
    try:
        import torch
    except ImportError:
        return

    if not torch.cuda.is_available():
        return

    GPU_MEMORY_ALLOCATED.set(torch.cuda.memory_allocated())
    GPU_MEMORY_RESERVED.set(torch.cuda.memory_reserved())
