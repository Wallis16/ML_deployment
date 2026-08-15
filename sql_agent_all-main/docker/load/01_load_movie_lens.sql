\connect movie_lens

COPY movies (movie_id, title, genres)
    FROM '/raw_data/movie_lens/movies.csv' WITH (FORMAT csv, HEADER true);

COPY links (movie_id, imdb_id, tmdb_id)
    FROM '/raw_data/movie_lens/links.csv' WITH (FORMAT csv, HEADER true);

COPY ratings (user_id, movie_id, rating, rated_at_epoch)
    FROM '/raw_data/movie_lens/ratings.csv' WITH (FORMAT csv, HEADER true);

COPY tags (user_id, movie_id, tag, tagged_at_epoch)
    FROM '/raw_data/movie_lens/tags.csv' WITH (FORMAT csv, HEADER true);
