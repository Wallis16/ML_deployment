"""Loads the schema reference and database-selection description files
written for this project (see schema_docs/ and metadata/)."""

from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DOCS_DIR = PROJECT_ROOT / "schema_docs"
METADATA_DIR = PROJECT_ROOT / "metadata"

DATABASES = ["movie_lens", "olist"]


@lru_cache
def get_database_description(database: str) -> str:
    return (METADATA_DIR / f"{database}_description.txt").read_text(encoding="utf-8")


@lru_cache
def get_schema_reference(database: str) -> str:
    return (SCHEMA_DOCS_DIR / f"{database}.txt").read_text(encoding="utf-8")


def get_all_database_descriptions() -> str:
    return "\n\n".join(
        f"### {db}\n{get_database_description(db)}" for db in DATABASES
    )
