-- Small routing database: holds one embedding per source database
-- (movie_lens, olist), used by the agent to pick which database a question
-- belongs to via a nearest-neighbor lookup instead of an LLM call.
CREATE DATABASE agent_metadata;
\connect agent_metadata

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE database_descriptions (
    database    TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    -- BAAI/bge-small-en-v1.5 output dimension
    embedding   vector(384) NOT NULL
);
