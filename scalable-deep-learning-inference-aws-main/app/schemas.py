from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8_000)
    max_new_tokens: int = Field(default=100, ge=1, le=512)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class GenerateResponse(BaseModel):
    response: str
    latency_ms: int
    tokens_generated: int
    tokens_per_second: float
    first_token_latency_ms: int | None = None


class HealthResponse(BaseModel):
    status: str


class DeviceInfo(BaseModel):
    index: int
    name: str
    total_memory_mb: int


class DeviceStatusResponse(BaseModel):
    model_loaded: bool
    inference_device: str
    cuda_available: bool
    gpu_count: int
    devices: list[DeviceInfo]
    note: str | None = None
