"""
Stage 5, 6, 7: Retrieval + Augmentation + Generation
Retrieves relevant chunks from pgvector, builds a grounded prompt, and
generates an answer using Gemini via ChatVertexAI. Returns the answer
along with the source documents it was grounded in.

Connects to Cloud SQL via the Cloud SQL Python Connector using IAM
authentication (see embed.py) — no Cloud SQL Auth Proxy needed.
"""
import os
import logging

import google.cloud.logging
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_vertexai import ChatVertexAI

from embed import get_embeddings, engine, COLLECTION_NAME
from langchain_postgres import PGVector

# Route Python logging through the Cloud Logging client so entries land in
# Cloud Logging (and are queryable by the log-based metric set up in Console).
_cloud_logging_client = google.cloud.logging.Client()
_cloud_logging_client.setup_logging()
logger = logging.getLogger("rag_pipeline")


# PROJECT_ID = "rag-pipe-mcp"
# REGION = "europe-west4"

PROJECT_ID = os.environ["PROJECT_ID"]
REGION = os.environ["REGION"]
GENERATION_MODEL = "gemini-2.5-flash"  # update to whichever Gemini model you intend to use
TOP_K = 4

PROMPT_TEMPLATE = """Answer the question using only the context below.
If the context doesn't contain enough information to answer, say so
clearly rather than guessing.

Context:
{context}

Question: {question}

Answer:"""

INSUFFICIENT_CONTEXT_MARKERS = [
    "does not contain enough information",
    "context does not contain",
    "not enough information",
    "cannot answer",
    "unable to answer",
]


def indicates_insufficient_context(answer: str) -> bool:
    """
    Heuristic check for whether the model's answer signals that retrieval
    didn't surface useful context. This is a lightweight string match, not
    a robust classifier — good enough for a POC signal, not production-grade
    retrieval-quality detection.
    """
    lowered = answer.lower()
    return any(marker in lowered for marker in INSUFFICIENT_CONTEXT_MARKERS)


def get_vectorstore() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection=engine,
        use_jsonb=True,
    )


def format_docs_with_sources(docs) -> str:
    """Join retrieved chunks into a single context block, tagging each with its source."""
    return "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


def build_rag_chain(vectorstore: PGVector):
    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    llm = ChatVertexAI(project=PROJECT_ID, location=REGION, model_name=GENERATION_MODEL)

    chain = (
        {
            "context": retriever | format_docs_with_sources,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever


def ask(question: str) -> dict:
    """
    Run the full retrieval-augmented generation flow for a single question.
    Returns the answer plus the list of source documents used.
    """
    vectorstore = get_vectorstore()
    chain, retriever = build_rag_chain(vectorstore)

    sources_docs = retriever.invoke(question)
    answer = chain.invoke(question)

    if indicates_insufficient_context(answer):
        logger.warning(
            "Answer indicates insufficient retrieved context",
            extra={
                "json_fields": {
                    "event": "insufficient_context",
                    "question": question,
                    "num_chunks_retrieved": len(sources_docs),
                }
            },
        )

    return {
        "question": question,
        "answer": answer,
        "sources": [doc.metadata.get("source", "unknown") for doc in sources_docs],
    }


if __name__ == "__main__":
    test_question = "What roles is this candidate applying for?"
    result = ask(test_question)

    print(f"Question: {result['question']}\n")
    print(f"Answer: {result['answer']}\n")
    print("Sources used:")
    for src in result["sources"]:
        print(f"  - {src}")