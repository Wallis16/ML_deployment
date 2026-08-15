"""Local embeddings (sentence-transformers) + pgvector nearest-neighbor
lookup used to pick which database a question belongs to.

Instead of pasting both database descriptions into the LLM prompt and asking
it to choose, this embeds the question with the same local model used to
embed each database's description (see metadata/*_description.txt) and picks
the closest one by cosine distance in Postgres (pgvector, agent_metadata db).
Runs fully offline/locally — no API call for this step.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from . import db
from .docs import DATABASES, get_database_description

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
ROUTING_DATABASE = "agent_metadata"


@lru_cache
def _model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _embed(text_: str) -> str:
    """Encodes text with the local model and returns it as a pgvector literal."""
    vector = _model().encode(text_, normalize_embeddings=True)
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


def sync_database_descriptions() -> None:
    """(Re)embeds metadata/*_description.txt and upserts them into pgvector.
    Idempotent — cheap to call on every startup; only re-embeds a database's
    description if its text actually changed."""
    engine = db.get_engine(ROUTING_DATABASE)
    with engine.begin() as conn:
        for database in DATABASES:
            description = get_database_description(database)
            conn.execute(
                text(
                    """
                    INSERT INTO database_descriptions (database, description, embedding)
                    VALUES (:database, :description, CAST(:embedding AS vector))
                    ON CONFLICT (database) DO UPDATE
                        SET description = EXCLUDED.description,
                            embedding = EXCLUDED.embedding
                    WHERE database_descriptions.description IS DISTINCT FROM EXCLUDED.description
                    """
                ),
                {"database": database, "description": description, "embedding": _embed(description)},
            )


def select_database(question: str) -> tuple[str, float]:
    """Returns (database, cosine_distance) for the description closest to
    the question. Lower distance = more relevant (0 = identical, 2 = opposite)."""
    engine = db.get_engine(ROUTING_DATABASE)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT database, embedding <=> CAST(:embedding AS vector) AS distance
                FROM database_descriptions
                ORDER BY distance ASC
                LIMIT 1
                """
            ),
            {"embedding": _embed(question)},
        ).one()
    return row.database, row.distance


if __name__ == "__main__":
    sync_database_descriptions()
    print(f"Synced embeddings for: {', '.join(DATABASES)}")
