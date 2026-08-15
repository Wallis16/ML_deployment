"""RAGAS-based evaluation of the SQL agent, testing three separate things:

1. test_rag_picks_the_right_database — the RAG step in isolation
   (agent/embeddings.py: local sentence-transformer + pgvector nearest-
   neighbor lookup). Scored with RAGAS's NonLLMContextPrecisionWithReference,
   comparing the retrieved database description against the reference one.

2. test_agent_calls_the_right_database_tool — the agent end-to-end: given
   its actual run, did it query the database it should have? Modeled as a
   tool call (tool name = database queried) and scored with RAGAS's
   ToolCallAccuracy.

3. test_final_report_is_correct — is the agent's final natural-language
   report factually correct, scored against a short reference answer with
   RAGAS's AnswerCorrectness (LLM-judged via Groq + local embeddings).

Run with:
    pytest test_ragas/ -v -s
"""

import os

import pytest
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.dataset_schema import MultiTurnSample, SingleTurnSample
from ragas.embeddings.base import LangchainEmbeddingsWrapper
from ragas.llms.base import LangchainLLMWrapper
from ragas.messages import AIMessage, HumanMessage, ToolCall
from ragas.metrics import AnswerCorrectness, AnswerSimilarity, NonLLMContextPrecisionWithReference, ToolCallAccuracy

from agent.docs import get_database_description
from agent.embeddings import EMBEDDING_MODEL_NAME, select_database
from agent.graph import build_graph
from agent.llm import MODEL as GROQ_MODEL

from .dataset import TEST_CASES

CONTEXT_PRECISION_THRESHOLD = 0.9
TOOL_CALL_THRESHOLD = 0.9
ANSWER_CORRECTNESS_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def agent_graph():
    return build_graph()


@pytest.fixture(scope="session")
def agent_results(agent_graph):
    """Runs every test question through the full agent exactly once, so the
    tool-call and final-report tests below don't each re-run (and re-bill)
    the same query."""
    results = {}
    for case in TEST_CASES:
        results[case.question] = agent_graph.invoke(
            {"question": case.question, "attempt": 0, "max_attempts": 3}
        )
    return results


@pytest.fixture(scope="session")
def context_precision():
    return NonLLMContextPrecisionWithReference()


@pytest.fixture(scope="session")
def tool_call_accuracy():
    return ToolCallAccuracy()


@pytest.fixture(scope="session")
def answer_correctness():
    # max_tokens is explicit because the default leaves room to get cut off
    # mid-JSON on longer answers (e.g. a top-5 list), which ragas treats as a
    # hard failure (LLMDidNotFinishException) rather than a low score.
    llm = LangchainLLMWrapper(ChatGroq(model=GROQ_MODEL, max_tokens=4096))
    # Reuses the same local model the agent's RAG step embeds with — no
    # OpenAI dependency, everything here runs against Groq + local weights.
    embeddings = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME))
    return AnswerCorrectness(llm=llm, embeddings=embeddings, answer_similarity=AnswerSimilarity(embeddings=embeddings))


# ---------------------------------------------------------------------------
# 1. Is the RAG step retrieving the right database?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c.question)
def test_rag_picks_the_right_database(case, context_precision):
    picked_database, distance = select_database(case.question)
    retrieved_description = get_database_description(picked_database)
    reference_description = get_database_description(case.expected_database)

    sample = SingleTurnSample(
        user_input=case.question,
        retrieved_contexts=[retrieved_description],
        reference_contexts=[reference_description],
    )
    score = context_precision.single_turn_score(sample)

    assert picked_database == case.expected_database, (
        f"RAG picked {picked_database!r}, expected {case.expected_database!r} "
        f"(cosine distance={distance:.4f})"
    )
    assert score >= CONTEXT_PRECISION_THRESHOLD


# ---------------------------------------------------------------------------
# 2. Does the agent actually query the right database?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c.question)
def test_agent_calls_the_right_database_tool(case, agent_results, tool_call_accuracy):
    result = agent_results[case.question]

    sample = MultiTurnSample(
        user_input=[
            HumanMessage(content=case.question),
            AIMessage(content="", tool_calls=[ToolCall(name=result["database"], args={})]),
        ],
        reference_tool_calls=[ToolCall(name=case.expected_database, args={})],
    )
    score = tool_call_accuracy.multi_turn_score(sample)

    assert result["database"] == case.expected_database
    assert score >= TOOL_CALL_THRESHOLD


# ---------------------------------------------------------------------------
# 3. Is the agent's final report correct?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c.question)
def test_final_report_is_correct(case, agent_results, answer_correctness):
    result = agent_results[case.question]
    assert not result.get("run_error"), f"query failed: {result.get('run_error')}"

    sample = SingleTurnSample(
        user_input=case.question,
        response=result["report"],
        reference=case.reference_answer,
    )
    score = answer_correctness.single_turn_score(sample)

    assert score >= ANSWER_CORRECTNESS_THRESHOLD, (
        f"answer_correctness={score:.2f} for {case.question!r}\nSQL: {result.get('query')}\nreport: {result['report']}"
    )
