from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_device_status() -> None:
    response = client.get("/device")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["model_loaded"], bool)
    assert body["inference_device"] in {"cpu", "cuda"}
    assert isinstance(body["cuda_available"], bool)
    assert isinstance(body["gpu_count"], int)
    assert isinstance(body["devices"], list)


def test_generate(monkeypatch) -> None:
    monkeypatch.setenv("SMOLLM_MOCK", "1")

    response = client.post(
        "/generate",
        json={"prompt": "What is AWS ECS?", "max_new_tokens": 32, "temperature": 0.1},
    )

    assert response.status_code == 200
    body = response.json()
    assert "AWS ECS" in body["response"]
    assert body["latency_ms"] >= 0
    assert body["tokens_generated"] > 0
    assert body["tokens_per_second"] >= 0


def test_generate_rejects_empty_prompt() -> None:
    response = client.post("/generate", json={"prompt": ""})

    assert response.status_code == 422
