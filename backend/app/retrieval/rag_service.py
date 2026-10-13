"""Project-scoped evidence ingestion and retrieval with stable-source upserts."""
import hashlib
import math
import re
from sqlalchemy.orm import Session
from app.models import DocumentChunk, ProjectDocument, ProjectRecord
from app.retrieval.chunking import chunk_text
from app.retrieval.embeddings import embed_texts, vector_from_json, vector_to_json

STABLE_SOURCE_PREFIXES = (
    "gmail:", "mock-jira:", "mock-confluence:", "jira:", "confluence:",
    "drive:", "upload:",
)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", text or "")}


def _keyword_score(query: str, text: str) -> float:
    q, d = _tokens(query), _tokens(text)
    if not q or not d:
        return 0.0
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
    """Rebuild the chunks for a source document; embedding failure falls back to keywords."""
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


def _stable_document_id(project_id: str, source: str) -> str:
    digest = hashlib.sha256(f"{project_id}\n{source}".encode("utf-8")).hexdigest()[:24]
    return f"DOC-{digest}"


def ingest_document(db: Session, project_id: str, title: str, source: str, content: str,
                    related_task_id: str | None = None, is_synthetic: bool = True) -> dict:
    """Upsert source records by stable identity so repeated syncs do not create copies.

    Known source namespaces (Gmail messages, synthetic/live connector records, Drive and
    uploads) are identified by project + source. Seeded/general documents retain a
    content fingerprint so two differently titled documents from the same named source
    are not accidentally merged.
    """
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise LookupError("Project not found")
    normalized_source = source.strip()
    normalized_title = title.strip()
    normalized = content.strip()
    stable_identity = normalized_source.lower().startswith(STABLE_SOURCE_PREFIXES)
    created = False
    updated = False

    document = None
    duplicates = []
    if stable_identity:
        duplicates = (db.query(ProjectDocument)
                      .filter(ProjectDocument.project_id == project_id,
                              ProjectDocument.source == normalized_source)
                      .order_by(ProjectDocument.document_id.asc()).all())
        if duplicates:
            document = duplicates[0]

        # Migrate legacy synthetic Jira IDs to task-based IDs when a task match is known.
        if document is None and normalized_source.startswith("mock-jira:") and related_task_id:
            legacy = (db.query(ProjectDocument)
                      .filter(ProjectDocument.project_id == project_id,
                              ProjectDocument.source.like("mock-jira:%"),
                              ProjectDocument.related_task_id == related_task_id)
                      .order_by(ProjectDocument.document_id.asc()).all())
            if legacy:
                duplicates = legacy
                document = legacy[0]
                document.source = normalized_source
    else:
        fingerprint = hashlib.sha256(
            f"{project_id}\n{normalized_source}\n{normalized_title}\n{normalized}".encode("utf-8")
        ).hexdigest()
        document_id = f"DOC-{fingerprint[:24]}"
        document = db.query(ProjectDocument).filter(ProjectDocument.document_id == document_id).first()
        if document is None:
            document = ProjectDocument(
                document_id=document_id, project_id=project_id, title=normalized_title,
                source=normalized_source, content=normalized, related_task_id=related_task_id,
                is_synthetic=is_synthetic,
            )
            db.add(document)
            db.flush()
            created = True

    # If old sync behavior left multiple rows under the same connector identity,
    # retain one stable document and delete its duplicate chunks/documents.
    if stable_identity and len(duplicates) > 1:
        for duplicate in duplicates[1:]:
            db.query(DocumentChunk).filter(DocumentChunk.document_id == duplicate.document_id).delete(synchronize_session=False)
            db.delete(duplicate)

    if stable_identity and document is None:
        document = ProjectDocument(
            document_id=_stable_document_id(project_id, normalized_source),
            project_id=project_id,
            title=normalized_title,
            source=normalized_source,
            content=normalized,
            related_task_id=related_task_id,
            is_synthetic=is_synthetic,
        )
        db.add(document)
        db.flush()
        created = True

    if document is None:
        raise RuntimeError("Could not create or locate the evidence document")

    content_changed = document.content != normalized or document.title != normalized_title
    metadata_changed = (document.source != normalized_source
                        or document.related_task_id != related_task_id
                        or document.is_synthetic != is_synthetic)
    if not created:
        updated = content_changed or metadata_changed
        document.title = normalized_title
        document.source = normalized_source
        document.content = normalized
        document.related_task_id = related_task_id
        document.is_synthetic = is_synthetic

    existing_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.document_id).count()
    if created or content_changed or existing_chunks == 0:
        chunks_count = index_document(db, document)
    else:
        chunks_count = existing_chunks

    db.commit()
    return {
        "document_id": document.document_id,
        "project_id": project_id,
        "title": document.title,
        "source": document.source,
        "created": created,
        "updated": updated,
        "chunks_indexed": chunks_count,
    }


def retrieve_evidence(db: Session, project_id: str, query: str, top_k: int = 5) -> dict:
    chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()
    if not chunks:
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
    chunked_document_ids = {chunk.document_id for chunk in chunks}
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
    # Newly created project briefs may not have embeddings/chunks yet. Keep these
    # unchunked source documents retrievable instead of silently dropping them as the
    # project acquires its first indexed connector document.
    for document_id, doc in docs_by_id.items():
        if document_id in chunked_document_ids:
            continue
        score = _keyword_score(query, doc.content)
        if score > 0:
            scored.append({
                "document_id": doc.document_id,
                "chunk_id": None,
                "title": doc.title,
                "source": doc.source,
                "content": doc.content,
                "related_task_id": doc.related_task_id,
                "score": round(float(score), 4),
            })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {"retrieval_mode": "embedding" if used_vectors else "keyword_fallback", "results": scored[:max(1, min(top_k, 10))]}
