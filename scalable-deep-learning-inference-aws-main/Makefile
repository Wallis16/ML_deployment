.PHONY: install test run docker-build docker-run benchmark

install:
	python -m pip install -r requirements.txt

test:
	SMOLLM_MOCK=1 pytest -q

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

docker-build:
	docker build -f docker/Dockerfile -t smollm-api .

docker-run:
	docker run --gpus all --env-file .env -p 8000:8000 smollm-api

benchmark:
	python scripts/benchmark.py --url http://localhost:8000 --requests 10
