"""
Stage 1: Ingestion
Downloads PDF files from the Cloud Storage ingestion bucket and loads them
into LangChain Document objects using PyPDFLoader.

Assumes PDFs are text-based (not scanned) — no OCR/Document AI needed.
"""

import os
import tempfile

from google.cloud import storage
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


PROJECT_ID = os.environ["PROJECT_ID"]
BUCKET_NAME = os.environ.get("INGESTION_BUCKET_NAME", "rag-pipe-mcp-ingestion")

# PROJECT_ID = "rag-pipe-mcp"
# BUCKET_NAME = "rag-pipe-mcp-ingestion" #ingestion bucket


def list_pdf_blobs(bucket_name: str) -> list:
    """Return all .pdf blobs in the given bucket."""
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    return [blob for blob in bucket.list_blobs() if blob.name.lower().endswith(".pdf")]


def load_documents_from_bucket(bucket_name: str = BUCKET_NAME) -> list[Document]:
    """
    Download each PDF from the bucket to a temp file, load it with
    PyPDFLoader, and return a flat list of Documents (one per page)
    with source metadata pointing back to the original GCS path.
    """
    blobs = list_pdf_blobs(bucket_name)
    if not blobs:
        raise ValueError(
            f"No PDF files found in gs://{bucket_name}. "
            f"Upload some with: gsutil cp your-file.pdf gs://{bucket_name}/"
        )

    all_documents = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for blob in blobs:
            local_path = os.path.join(tmp_dir, os.path.basename(blob.name))
            blob.download_to_filename(local_path)

            loader = PyPDFLoader(local_path)
            pages = loader.load()

            # Overwrite the source metadata to point at GCS, not the temp file
            for page in pages:
                page.metadata["source"] = f"gs://{bucket_name}/{blob.name}"

            all_documents.extend(pages)
            print(f"Loaded {len(pages)} page(s) from {blob.name}")

    print(f"Total pages loaded: {len(all_documents)}")
    return all_documents


if __name__ == "__main__":
    docs = load_documents_from_bucket()
    if docs:
        print("\n--- Sample of first loaded page ---")
        print(f"Source: {docs[0].metadata.get('source')}")
        print(f"Content preview: {docs[0].page_content[:300]}")