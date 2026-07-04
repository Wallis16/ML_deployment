import argparse
import statistics
import time

import requests


def run_benchmark(url: str, prompt: str, requests_count: int) -> None:
    latencies = []
    token_rates = []

    for index in range(1, requests_count + 1):
        started = time.perf_counter()
        response = requests.post(
            f"{url.rstrip('/')}/generate",
            json={"prompt": prompt, "max_new_tokens": 100, "temperature": 0.7},
            timeout=120,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()

        body = response.json()
        latencies.append(elapsed_ms)
        token_rates.append(body.get("tokens_per_second", 0.0))
        print(
            f"{index:03d}: {elapsed_ms:.0f} ms, "
            f"{body.get('tokens_generated', 0)} tokens, "
            f"{body.get('tokens_per_second', 0.0)} tokens/sec"
        )

    print("\nSummary")
    print(f"Requests: {requests_count}")
    print(f"Latency p50: {statistics.median(latencies):.0f} ms")
    print(f"Latency avg: {statistics.mean(latencies):.0f} ms")
    print(f"Tokens/sec avg: {statistics.mean(token_rates):.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SmolLM inference API.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--prompt", default="Explain AWS ECS in one sentence.")
    args = parser.parse_args()

    run_benchmark(args.url, args.prompt, args.requests)


if __name__ == "__main__":
    main()
