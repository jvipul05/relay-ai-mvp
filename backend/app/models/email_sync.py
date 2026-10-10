"""Persistence for Outlook sync connections and short-lived OAuth flows."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from app.core.database import Base


class EmailSyncConnection(Base):
    __tablename__ = "relay_email_sync_connections"

    project_id = Column(String(64), ForeignKey("relay_projects.project_id", ondelete="CASCADE"), primary_key=True)
    provider = Column(String(32), nullable=False, default="microsoft_graph")
    connected_email = Column(String(320), nullable=True)
    encrypted_token_cache = Column(Text, nullable=False)
    keywords_json = Column(Text, nullable=False, default="[]")
    sync_enabled = Column(Boolean, nullable=False, default=False)
    interval_minutes = Column(Integer, nullable=False, default=15)
    last_sync_at = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(32), nullable=False, default="connected")
    last_sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class EmailOAuthState(Base):
    __tablename__ = "relay_email_oauth_states"

    state = Column(String(128), primary_key=True)
    project_id = Column(String(64), ForeignKey("relay_projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    flow_json = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
