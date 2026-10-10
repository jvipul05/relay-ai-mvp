"""Searchable chunks derived from source documents for Relay RAG."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "relay_document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_relay_document_chunk_index"),
    )

    chunk_id = Column(String(80), primary_key=True)
    document_id = Column(String(64), ForeignKey("relay_project_documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(64), ForeignKey("relay_projects.project_id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
