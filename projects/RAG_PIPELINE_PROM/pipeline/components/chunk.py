"""
Stage 2: Chunking
Splits loaded Documents into smaller overlapping chunks sized for embedding.
Pure Python — no GCP calls in this stage.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def chunk_documents(
    documents: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """
    Split a list of Documents into smaller chunks.
    Metadata (including 'source') is preserved on every resulting chunk.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)
    print(f"Split {len(documents)} page(s) into {len(chunks)} chunk(s)")
    return chunks


if __name__ == "__main__":
    from ingest import load_documents_from_bucket

    docs = load_documents_from_bucket()
    chunks = chunk_documents(docs)

    if chunks:
        print("\n--- Sample chunk ---")
        print(f"Source: {chunks[0].metadata.get('source')}")
        print(f"Length: {len(chunks[0].page_content)} chars")
        print(f"Content preview: {chunks[0].page_content[:300]}")