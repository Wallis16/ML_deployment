from locust import HttpUser, between, task


GENERATE_PROMPT = "Who is Ronaldo?"
GENERATE_TEMPERATURE = 0
MAX_NEW_TOKENS = 100


class GenerateLatencyUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def generate(self) -> None:
        payload = {
            "prompt": GENERATE_PROMPT,
            "max_new_tokens": MAX_NEW_TOKENS,
            "temperature": GENERATE_TEMPERATURE,
        }

        with self.client.post(
            "/generate",
            json=payload,
            name="POST /generate",
            catch_response=True,
            timeout=120,
        ) as response:
            print(response.request.url)
            print(response.status_code)
            print(response.text)
            if response.status_code != 200:
                response.failure(f"Unexpected status code: {response.status_code}")
                return

            try:
                body = response.json()
            except ValueError as exc:
                response.failure(f"Response is not valid JSON: {exc}")
                return

            required_fields = {
                "response",
                "latency_ms",
                "tokens_generated",
                "tokens_per_second",
            }
            missing_fields = required_fields.difference(body)
            if missing_fields:
                response.failure(
                    f"Missing response fields: {', '.join(sorted(missing_fields))}"
                )
                return

            if body["latency_ms"] < 0:
                response.failure("latency_ms must be greater than or equal to 0")
                return

            if body["tokens_generated"] <= 0:
                response.failure("tokens_generated must be greater than 0")
                return

            response.success()
