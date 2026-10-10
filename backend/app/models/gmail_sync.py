"""Persistent Gmail OAuth and sync state for Relay."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class GmailConnection(Base):
    __tablename__ = "relay_gmail_connections"
    project_id = Column(String(64), primary_key=True, index=True)
    email_address = Column(String(320), nullable=True)
    encrypted_credentials = Column(Text, nullable=False)
    connected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GmailSyncConfig(Base):
    __tablename__ = "relay_gmail_sync_config"
    project_id = Column(String(64), primary_key=True, index=True)
    keywords_json = Column(Text, nullable=False, default='[]')
    interval_minutes = Column(Integer, nullable=False, default=15)
    enabled = Column(Boolean, nullable=False, default=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GmailOAuthState(Base):
    __tablename__ = "relay_gmail_oauth_states"
    state = Column(String(128), primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # Persist PKCE verifier so callback can complete token exchange across HTTP requests.
    code_verifier = Column(Text, nullable=True)


class GmailProcessedMessage(Base):
    __tablename__ = "relay_gmail_processed_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False)
    document_id = Column(String(64), nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "gmail_message_id", name="uq_relay_gmail_project_message"),)
