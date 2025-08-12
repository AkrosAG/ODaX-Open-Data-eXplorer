from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB  # optional here
import pandas as pd
import json

engine = create_engine("postgresql+psycopg2://postgres:odax123@localhost:5433/odax_test")

df = pd.DataFrame([{
    "name": "Source 1",
    "description": "Example",
    "url": "http://example.com",
    "license": "MIT",
    "raw_source_metadata": {}          # dict -> will JSON-encode
}])

# JSON-encode dicts so psycopg2 receives a string
df["raw_source_metadata"] = df["raw_source_metadata"].apply(json.dumps)

df.to_sql("sources", engine, if_exists="append", index=False)

print(pd.read_sql("SELECT * FROM sources", engine))


# After psql -h localhost -p 5433 -U postgres -d odax_test and password insertation you can also access the table by:
'''
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
'''