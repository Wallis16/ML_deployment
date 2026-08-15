-- Bare tables only (no PK/FK/indexes yet) so the bulk COPY load in
-- docker/load/ isn't slowed down by constraint checks. Constraints are
-- added afterwards by docker/load/03_movie_lens_constraints.sql.
\connect movie_lens

CREATE TABLE movies (
    movie_id INTEGER NOT NULL,
    title    TEXT    NOT NULL,
    genres   TEXT
);

CREATE TABLE links (
    movie_id INTEGER NOT NULL,
    imdb_id  TEXT    NOT NULL,
    tmdb_id  INTEGER
);

CREATE TABLE ratings (
    user_id         INTEGER NOT NULL,
    movie_id        INTEGER NOT NULL,
    rating          NUMERIC(2,1) NOT NULL,
    rated_at_epoch  BIGINT NOT NULL
);

CREATE TABLE tags (
    id              BIGSERIAL,
    user_id         INTEGER NOT NULL,
    movie_id        INTEGER NOT NULL,
    tag             TEXT,
    tagged_at_epoch BIGINT NOT NULL
);
