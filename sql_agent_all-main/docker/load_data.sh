#!/usr/bin/env bash
# Bulk-loads the CSVs under ../raw_data into the movie_lens and olist
# databases. Run once after `docker compose up -d`, from the docker/ folder.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

set -a
source ./.env
set +a

run() {
    echo "-- running $1"
    docker exec -i agent_database psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" < "$1"
}

run load/01_load_movie_lens.sql
run load/02_load_olist.sql
run load/03_movie_lens_constraints.sql
run load/04_olist_constraints.sql

echo "Done."
