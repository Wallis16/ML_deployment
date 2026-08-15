# PostgreSQL container

Single PostgreSQL 16 container (image: `pgvector/pgvector:pg16` — same
Postgres 16, plus the `pgvector` extension) with a named volume for
persistence and three databases:

- `movie_lens` — `movies`, `links`, `ratings`, `tags` (backs
  [../raw_data/movie_lens](../raw_data/movie_lens))
- `olist` — `customers`, `sellers`, `geolocation`, `products`, `orders`,
  `order_items`, `order_payments`, `order_reviews`,
  `product_category_name_translation` (backs
  [../raw_data/olist](../raw_data/olist))
- `agent_metadata` — one `vector(384)` embedding per database description
  (`pgvector`), used by [../agent](../agent) to pick which database a
  question belongs to. Populate/refresh with `python -m agent.embeddings`.

## Usage

```bash
cd docker
docker compose up -d   # creates the container, volume, and empty schemas
./load_data.sh          # bulk-loads the CSVs (run once; ratings.csv is ~32M rows)
```

Connection details (from `.env`):

- Host: `localhost`
- Port: `5433` (`POSTGRES_PORT`) — 5432 was already taken by another local container
- User: `postgres` (`POSTGRES_USER`)
- Password: `postgres` (`POSTGRES_PASSWORD`)
- Databases: `movie_lens`, `olist`, `agent_metadata`

Edit `.env` before first startup to change credentials/port.

## How it works

- `initdb/` runs automatically, once, only when the data volume is empty
  (first container init):
  - `01_create_databases.sql` — creates the two data databases
  - `02_movie_lens_schema.sql` / `03_olist_schema.sql` — bare tables, no
    primary keys/foreign keys/indexes yet
  - `04_agent_metadata.sql` — creates the `agent_metadata` database, enables
    `pgvector`, and creates the `database_descriptions` table
- `load/` is run manually via `load_data.sh` (not part of initdb, so it
  doesn't block container startup):
  - `01_load_movie_lens.sql` / `02_load_olist.sql` — server-side `COPY` from
    the CSVs, which are bind-mounted read-only into the container at
    `/raw_data`
  - `03_movie_lens_constraints.sql` / `04_olist_constraints.sql` — adds
    primary keys, foreign keys, and indexes after the bulk load (much faster
    than maintaining them row-by-row during `COPY`)

`products.product_category_name` is intentionally not a foreign key to
`product_category_name_translation`: a few categories in the source data
have no translation row. `order_reviews` uses a surrogate `id` primary key
because `review_id` is not globally unique in the source data.

If you change `.env` values after the volume already exists, they won't
retroactively rename/recreate anything — see "start fresh" below.

## Notes

- Data persists in the named volume `sql-agent-postgres-data`. To wipe it and
  start fresh (re-running initdb from scratch):

  ```bash
  docker compose down -v
  docker compose up -d
  ./load_data.sh
  python -m agent.embeddings   # from the project root — populates agent_metadata
  ```

- To stop without deleting data:

  ```bash
  docker compose down
  ```
