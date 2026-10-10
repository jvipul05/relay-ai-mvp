"""Index source documents and retrieve project-scoped evidence for RAG."""
import hashlib
import math
import re
from sqlalchemy.orm import Session
from app.models import DocumentChunk, ProjectDocument, ProjectRecord
from app.retrieval.chunking import chunk_text
from app.retrieval.embeddings import embed_texts, vector_from_json, vector_to_json


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", text or "")}


def _keyword_score(query: str, text: str) -> float:
    q, d = _tokens(query), _tokens(text)
    if not q or not d:
        return 0.0
    # Simple normalized lexical score. Semantic ranking uses embeddings when available.
    return len(q & d) / math.sqrt(len(q) * len(d))


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _chunk_id(document_id: str, index: int, content: str) -> str:
    digest = hashlib.sha256(f"{document_id}:{index}:{content}".encode("utf-8")).hexdigest()[:32]
    return f"CHK-{digest}"


def index_document(db: Session, document: ProjectDocument) -> int:
    """Idempotently replace chunks for a source document and store embeddings if available."""
    chunks = chunk_text(document.content)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.document_id).delete(synchronize_session=False)
    vectors = embed_texts(chunks)
    for index, content in enumerate(chunks):
        vector = vectors[index] if vectors and index < len(vectors) else None
        db.add(DocumentChunk(
            chunk_id=_chunk_id(document.document_id, index, content),
            document_id=document.document_id,
            project_id=document.project_id,
            chunk_index=index,
            content=content,
            embedding_json=vector_to_json(vector),
        ))
    db.flush()
    return len(chunks)


def reindex_project_documents(db: Session, project_id: str) -> dict:
    documents = db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).order_by(ProjectDocument.document_id.asc()).all()
    total_chunks = 0
    for document in documents:
        total_chunks += index_document(db, document)
    db.commit()
    return {"project_id": project_id, "documents_indexed": len(documents), "chunks_indexed": total_chunks}


def ingest_document(db: Session, project_id: str, title: str, source: str, content: str, related_task_id: str | None = None, is_synthetic: bool = True) -> dict:
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise LookupError("Project not found")
    normalized = content.strip()
    fingerprint = hashlib.sha256(f"{project_id}\n{source.strip()}\n{title.strip()}\n{normalized}".encode("utf-8")).hexdigest()
    document_id = f"DOC-{fingerprint[:24]}"
    document = db.query(ProjectDocument).filter(ProjectDocument.document_id == document_id).first()
    created = document is None
    if document is None:
        document = ProjectDocument(
            document_id=document_id,
            project_id=project_id,
            title=title.strip(),
            source=source.strip(),
            content=normalized,
            related_task_id=related_task_id,
            is_synthetic=is_synthetic,
        )
        db.add(document)
        db.flush()
    existing_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()
    if existing_chunks == 0:
        chunks_count = index_document(db, document)
    else:
        chunks_count = existing_chunks
    db.commit()
    return {"document_id": document_id, "project_id": project_id, "title": document.title,
            "source": document.source, "created": created, "chunks_indexed": chunks_count}


def retrieve_evidence(db: Session, project_id: str, query: str, top_k: int = 5) -> dict:
    chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()
    if not chunks:
        # Existing seeded documents can be searched before the first explicit reindex.
        docs = db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).all()
        candidates = [{"document_id": doc.document_id, "title": doc.title, "source": doc.source,
                       "content": doc.content, "related_task_id": doc.related_task_id,
                       "score": _keyword_score(query, doc.content)} for doc in docs]
        candidates = sorted((item for item in candidates if item["score"] > 0), key=lambda item: item["score"], reverse=True)[:top_k]
        return {"retrieval_mode": "keyword_fallback", "results": candidates}

    query_vectors = embed_texts([query])
    query_vector = query_vectors[0] if query_vectors else None
    docs_by_id = {doc.document_id: doc for doc in db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).all()}
    scored = []
    used_vectors = bool(query_vector) and any(vector_from_json(chunk.embedding_json) for chunk in chunks)
    for chunk in chunks:
        doc = docs_by_id.get(chunk.document_id)
        if not doc:
            continue
        vector = vector_from_json(chunk.embedding_json)
        score = _cosine(query_vector, vector) if used_vectors and query_vector and vector else _keyword_score(query, chunk.content)
        if score > 0:
            scored.append({"document_id": doc.document_id, "chunk_id": chunk.chunk_id,
                           "title": doc.title, "source": doc.source, "content": chunk.content,
                           "related_task_id": doc.related_task_id, "score": round(float(score), 4)})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {"retrieval_mode": "embedding" if used_vectors else "keyword_fallback", "results": scored[:max(1, min(top_k, 10))]}
