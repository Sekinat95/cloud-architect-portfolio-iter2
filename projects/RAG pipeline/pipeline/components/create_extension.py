"""
One-time setup: creates the pgvector extension in the database.
Must run with a superuser role (postgres), not the IAM service account,
since IAM-authenticated users lack privilege to create extensions.
"""

import os
from google.cloud.sql.connector import Connector
import sqlalchemy

PROJECT_ID = os.environ["PROJECT_ID"]
REGION = os.environ["REGION"]
INSTANCE_NAME = os.environ["CLOUD_SQL_CONNECTION_NAME"]
DB_NAME = os.environ["DB_NAME"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

connector = Connector()


def getconn():
    return connector.connect(
        INSTANCE_NAME,
        "pg8000",
        user="postgres",
        password=POSTGRES_PASSWORD,
        db=DB_NAME,
        ip_type="PRIVATE",
    )


engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)

with engine.connect() as conn:
    conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector;"))
    conn.commit()
    print("pgvector extension created (or already exists).")