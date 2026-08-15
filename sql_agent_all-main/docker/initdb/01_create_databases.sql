-- Runs once, on first container initialization (empty data volume),
-- via the postgres image's docker-entrypoint-initdb.d mechanism.
CREATE DATABASE movie_lens;
CREATE DATABASE olist;
