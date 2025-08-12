# Usage of postgres in podman container
After psql -h localhost -p 5433 -U postgres -d odax_test and password insertation you can also access the table by:

-- where am I connected?
\conninfo
SHOW port;
SELECT current_database(), current_user;

-- does the table exist where I’m looking?
\dt public.sources

-- how many rows?
SELECT count(*) FROM public.sources;

-- inspect latest rows
SELECT * FROM public.sources ORDER BY source_id DESC LIMIT 5;

# Usage of postgres in docker container by Apache Superset via connector 
postgresql+psycopg2://postgres:odax123@host.docker.internal:5433/odax_test
oder auch 
postgresql+psycopg2://postgres:odax123@localhost:5433/odax_test
