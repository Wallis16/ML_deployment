\connect movie_lens

ALTER TABLE movies ADD PRIMARY KEY (movie_id);

ALTER TABLE links
    ADD PRIMARY KEY (movie_id),
    ADD FOREIGN KEY (movie_id) REFERENCES movies (movie_id);

ALTER TABLE ratings
    ADD PRIMARY KEY (user_id, movie_id),
    ADD FOREIGN KEY (movie_id) REFERENCES movies (movie_id);
CREATE INDEX ratings_movie_id_idx ON ratings (movie_id);

ALTER TABLE tags
    ADD PRIMARY KEY (id),
    ADD FOREIGN KEY (movie_id) REFERENCES movies (movie_id);
CREATE INDEX tags_movie_id_idx ON tags (movie_id);
CREATE INDEX tags_user_id_idx ON tags (user_id);
