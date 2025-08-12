from sqlalchemy import create_engine
import pandas as pd
import json

engine = create_engine(
    "postgresql+psycopg2://postgres:odax123@localhost:5433/odax_test"
)

df = pd.DataFrame(
    [
        {
            "name": "Source 1",
            "description": "Example",
            "url": "http://example.com",
            "license": "MIT",
            "raw_source_metadata": {},  # dict -> will JSON-encode
        }
    ]
)

# JSON-encode dicts so psycopg2 receives a string
df["raw_source_metadata"] = df["raw_source_metadata"].apply(json.dumps)

df.to_sql("sources", engine, if_exists="append", index=False)

print(pd.read_sql("SELECT * FROM sources", engine))
