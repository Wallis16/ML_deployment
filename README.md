# ML_deployment

A collection of end-to-end ML deployment projects, each written up in detail on my [Substack](https://digenessilva.substack.com).

## [scalable-deep-learning-inference-aws-main](scalable-deep-learning-inference-aws-main/)

A GPU-ready FastAPI service that serves `HuggingFaceTB/SmolLM2-360M-Instruct` for text generation, built to run locally first and then deploy to AWS ECS. It covers the full path from a local Docker/Compose setup with an NVIDIA CUDA base image, through Prometheus metrics and Locust load testing, to Terraform configs for both EC2 and ECS deployment targets. Read the full write-up: [How to build a scalable service for deep learning inference on AWS](https://digenessilva.substack.com/p/how-to-build-a-scalable-service-for?r=nl1z2).

## [sql_agent_all-main](sql_agent_all-main/)

A LangGraph agent that turns a natural-language question into SQL, runs it against one of two Postgres databases (MovieLens or Olist), and returns a plain-language report with an optional chart — wrapped in a FastAPI service, a Streamlit UI, Locust load tests, and a RAGAS eval suite. This project is documented across a three-part series on going from a from-scratch agent to a production system: [Part 1](https://digenessilva.substack.com/p/ai-agent-from-scratch-to-production?r=nl1z2), [Part 2](https://digenessilva.substack.com/p/ai-agent-from-scratch-to-production-8da?r=nl1z2), and [Part 3](https://digenessilva.substack.com/p/ai-agent-from-scratch-to-production-98c?r=nl1z2).
