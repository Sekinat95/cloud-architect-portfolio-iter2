
import os
from google.cloud.sql.connector import Connector
import sqlalchemy
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

PROJECT_ID = os.environ["PROJECT_ID"]  
REGION = os.environ["REGION"]          
INSTANCE_NAME = os.environ["CLOUD_SQL_CONNECTION_NAME"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"].replace(".gserviceaccount.com", "")

# PROJECT_ID = "rag-pipe-mcp-dev"
# REGION = "europe-west4"
# INSTANCE_NAME = f"{PROJECT_ID}:{REGION}:{PROJECT_ID}-pg"
# DB_NAME = "ragdb-dev"
# DB_USER = "rag-pipe-mcp-dev-pipeline@rag-pipe-mcp-dev.iam"  # SA email, .gserviceaccount.com stripped

COLLECTION_NAME = "rag_poc_chunks"
EMBEDDING_MODEL = "text-embedding-004"

connector = Connector()

def getconn():
    return connector.connect(
        INSTANCE_NAME,
        "pg8000",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type="PRIVATE",
    )

engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)


def get_embeddings():
    return VertexAIEmbeddings(project=PROJECT_ID, location=REGION, model_name=EMBEDDING_MODEL)


def embed_and_store(chunks: list[Document]) -> PGVector:
    embeddings = get_embeddings()
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=engine,
        use_jsonb=True,
    )
    ids = vectorstore.add_documents(chunks)
    print(f"Embedded and stored {len(ids)} chunk(s) in collection '{COLLECTION_NAME}'")
    return vectorstore
if __name__ == "__main__":
    from ingest import load_documents_from_bucket
    from chunk import chunk_documents

    docs = load_documents_from_bucket()
    chunks = chunk_documents(docs)
    embed_and_store(chunks)