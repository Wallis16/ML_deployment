"""FastAPI wrapper exposing the SQL agent (defined in ../agent) as a single
HTTP endpoint.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.graph import build_graph
from agent.tools import OUTPUT_DIR

logger = logging.getLogger("sql_agent_api")

app = FastAPI(
    title="SQL Agent API",
    description="Answers a natural-language question over the movie_lens and olist "
    "databases: picks the right database, writes and validates SQL, runs it, and "
    "returns a plain-language report plus an optional chart.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# Build the graph once at import time — reused (and safe to share) across requests.
_graph = build_graph()


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        examples=["What are the top 5 highest-rated movies with at least 100 ratings?"],
    )
    max_attempts: int = Field(3, ge=1, le=10, description="Max SQL-generation retries")


class QueryResponse(BaseModel):
    database: Optional[str] = None
    sql: Optional[str] = None
    report: Optional[str] = None
    plot_url: Optional[str] = None
    error: Optional[str] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = _graph.invoke({"question": request.question, "max_attempts": request.max_attempts})
    except Exception as exc:
        logger.exception("Unhandled error running the agent for question: %r", request.question)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    plot_url = None
    if result.get("plot_path"):
        plot_url = f"/output/{Path(result['plot_path']).name}"

    return QueryResponse(
        database=result.get("database"),
        sql=result.get("query"),
        report=result.get("report"),
        plot_url=plot_url,
        error=result.get("run_error"),
    )
