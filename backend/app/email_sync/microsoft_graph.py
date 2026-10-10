"""OAuth, scheduled Microsoft Graph mail sync, and RAG upsert helpers.

Read-only delegated permissions are used. This module never sends, deletes, or modifies mail.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode

import msal
import requests
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import EmailOAuthState, EmailSyncConnection, ProjectDocument, ProjectRecord
from app.retrieval.rag_service import index_document, ingest_document

SCOPES = ["User.Read", "Mail.Read"]  # MSAL adds openid/profile/offline_access as needed
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_INTERVAL_MINUTES = 15
MAX_MESSAGES_PER_RUN = 100
INITIAL_LOOKBACK_DAYS = 7


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else value


def _client_id() -> str:
    value = _env("MICROSOFT_CLIENT_ID")
    if not value:
        raise RuntimeError("Set MICROSOFT_CLIENT_ID in backend/.env using your Microsoft Entra app registration.")
    return value


def _authority() -> str:
    tenant = _env("MICROSOFT_TENANT_ID", "organizations") or "organizations"
    return f"https://login.microsoftonline.com/{tenant}"


def _redirect_uri() -> str:
    return _env("MICROSOFT_REDIRECT_URI", "http://127.0.0.1:8000/api/email/microsoft/callback") or "http://127.0.0.1:8000/api/email/microsoft/callback"


def _fernet() -> Fernet:
    key = _env("RELAY_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Set RELAY_TOKEN_ENCRYPTION_KEY in backend/.env; generate one with the README command.")
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise RuntimeError("RELAY_TOKEN_ENCRYPTION_KEY is invalid; generate a Fernet key and restart the backend.") from exc


def _serialize_cache(cache: msal.SerializableTokenCache) -> str:
    return _fernet().encrypt(cache.serialize().encode("utf-8")).decode("ascii")


def _deserialize_cache(encrypted: str) -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    try:
        serialized = _fernet().decrypt(encrypted.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Stored Microsoft token cache cannot be decrypted. Check the original RELAY_TOKEN_ENCRYPTION_KEY.") from exc
    cache.deserialize(serialized)
    return cache


def _client(cache: msal.SerializableTokenCache | None = None) -> msal.PublicClientApplication:
    kwargs: dict[str, Any] = {"client_id": _client_id(), "authority": _authority()}
    if cache is not None:
        kwargs["token_cache"] = cache
    return msal.PublicClientApplication(**kwargs)


def create_auth_flow(project_id: str) -> tuple[str, str, dict[str, Any]]:
    # Validate encryption configuration before initiating an OAuth flow.
    _fernet()
    app = _client()
    flow = app.initiate_auth_code_flow(scopes=SCOPES, redirect_uri=_redirect_uri())
    if not flow or "auth_uri" not in flow or "state" not in flow:
        raise RuntimeError("Microsoft sign-in flow could not be created.")
    return flow["state"], flow["auth_uri"], flow


def complete_auth_flow(db: Session, state: str, query_params: dict[str, str]) -> tuple[str, str | None]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(EmailOAuthState).filter(EmailOAuthState.expires_at < now).delete(synchronize_session=False)
    record = db.query(EmailOAuthState).filter(EmailOAuthState.state == state).first()
    if not record:
        raise ValueError("OAuth state is missing, expired, or already used. Start Connect again.")
    flow = json.loads(record.flow_json)
    project_id = record.project_id
    try:
        cache = msal.SerializableTokenCache()
        result = _client(cache).acquire_token_by_auth_code_flow(flow, query_params)
        if "access_token" not in result:
            message = result.get("error_description") or result.get("error") or "Microsoft sign-in failed."
            raise ValueError(message[:500])
        profile = requests.get(f"{GRAPH_BASE}/me", headers={"Authorization": f"Bearer {result['access_token']}"}, timeout=20)
        profile.raise_for_status()
        user = profile.json()
        connection = db.query(EmailSyncConnection).filter(EmailSyncConnection.project_id == project_id).first()
        if connection is None:
            connection = EmailSyncConnection(project_id=project_id, encrypted_token_cache=_serialize_cache(cache))
            db.add(connection)
        connection.connected_email = user.get("mail") or user.get("userPrincipalName")
        connection.encrypted_token_cache = _serialize_cache(cache)
        connection.last_sync_status = "connected"
        connection.last_sync_error = None
        db.delete(record)
        db.commit()
        return project_id, connection.connected_email
    except Exception:
        db.rollback()
        raise


def _access_token(connection: EmailSyncConnection) -> tuple[str, str]:
    cache = _deserialize_cache(connection.encrypted_token_cache)
    app = _client(cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0] if accounts else None) if accounts else None
    if not result or "access_token" not in result:
        raise RuntimeError("Microsoft session expired or consent was revoked. Reconnect Outlook for this project.")
    # MSAL refreshes the serialized cache when a refresh token is used.
    connection.encrypted_token_cache = _serialize_cache(cache)
    return result["access_token"], connection.connected_email or ""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value or "")
        extracted = " ".join(parser.parts)
        if extracted:
            return re.sub(r"\s+", " ", extracted).strip()
    except Exception:
        pass
    return re.sub(r"<[^>]+>", " ", value or "").strip()


def _matches_keywords(subject: str, body: str, keywords: list[str]) -> bool:
    # Fail closed: no configured project keywords means no email is ingested.
    haystack = f"{subject}\n{body}".casefold()
    return bool(keywords) and any(keyword.casefold() in haystack for keyword in keywords if keyword.strip())


def _message_content(message: dict[str, Any]) -> tuple[str, str]:
    subject = (message.get("subject") or "(No subject)").strip()[:250]
    body_obj = message.get("body") or {}
    body = _plain_text(body_obj.get("content") or message.get("bodyPreview") or "")
    sender = ((message.get("from") or {}).get("emailAddress") or {}).get("address") or "unknown"
    received = message.get("receivedDateTime") or "unknown"
    content = f"Email subject: {subject}\nFrom: {sender}\nReceived: {received}\n\n{body}".strip()
    return subject, content


def _upsert_email_document(db: Session, project_id: str, message: dict[str, Any], connected_email: str) -> bool:
    subject, content = _message_content(message)
    if len(content) < 20:
        return False
    message_id = message.get("id")
    if not message_id:
        return False
    source = f"outlook:{project_id}:{message_id}"[:255]
    document = db.query(ProjectDocument).filter(
        ProjectDocument.project_id == project_id,
        ProjectDocument.source == source,
    ).first()
    if document is None:
        ingest_document(db, project_id, subject, source, content, None, False)
        return True
    if document.content != content or document.title != subject:
        document.title = subject
        document.content = content
        document.is_synthetic = False
        index_document(db, document)
        db.commit()
    return False


def sync_project_emails(db: Session, project_id: str, *, force: bool = False) -> dict[str, Any]:
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise LookupError("Project not found")
    connection = db.query(EmailSyncConnection).filter(EmailSyncConnection.project_id == project_id).first()
    if not connection:
        raise LookupError("Outlook is not connected for this project. Connect first.")
    keywords = json.loads(connection.keywords_json or "[]")
    if not keywords:
        raise ValueError("Configure at least one project keyword before syncing. No emails have been ingested.")
    if not force and not connection.sync_enabled:
        return {"project_id": project_id, "status": "disabled", "message": "Scheduled sync is disabled."}

    try:
        connection.last_attempt_at = datetime.now(timezone.utc).replace(tzinfo=None)
        previous_cursor = connection.last_sync_at
        db.commit()
        access_token, connected_email = _access_token(connection)
        if previous_cursor:
            since = previous_cursor.replace(tzinfo=timezone.utc)
        else:
            since = datetime.now(timezone.utc) - timedelta(days=INITIAL_LOOKBACK_DAYS)
        since_text = since.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Prefer": 'outlook.body-content-type="text"',
        }
        params = {
            "$select": "id,subject,from,receivedDateTime,body,bodyPreview,webLink",
            "$filter": f"receivedDateTime ge {since_text}",
            "$orderby": "receivedDateTime asc",
            "$top": "50",
        }
        url = f"{GRAPH_BASE}/me/mailFolders/inbox/messages?{urlencode(params)}"
        scanned = ingested = 0
        newest = since
        while url and scanned < MAX_MESSAGES_PER_RUN:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code in (401, 403):
                raise RuntimeError("Microsoft Graph denied mail access. Reconnect and confirm delegated Mail.Read permission.")
            response.raise_for_status()
            payload = response.json()
            for message in payload.get("value", []):
                scanned += 1
                received = message.get("receivedDateTime")
                if received:
                    try:
                        parsed = datetime.fromisoformat(received.replace("Z", "+00:00")).astimezone(timezone.utc)
                        if parsed.replace(tzinfo=None) > newest.replace(tzinfo=None):
                            newest = parsed
                    except ValueError:
                        pass
                subject, content = _message_content(message)
                if _matches_keywords(subject, content, keywords):
                    if _upsert_email_document(db, project_id, message, connected_email):
                        ingested += 1
                if scanned >= MAX_MESSAGES_PER_RUN:
                    break
            url = payload.get("@odata.nextLink") if scanned < MAX_MESSAGES_PER_RUN else None
        # Advance by a small overlap to avoid losing messages at timestamp boundaries;
        # upsert-by-message-id prevents duplicate documents during the overlap.
        proposed_cursor = max(newest, datetime.now(timezone.utc)) - timedelta(seconds=2)
        if previous_cursor:
            proposed_cursor = max(proposed_cursor, previous_cursor.replace(tzinfo=timezone.utc))
        connection.last_sync_at = proposed_cursor.replace(tzinfo=None)
        connection.last_success_at = datetime.now(timezone.utc).replace(tzinfo=None)
        connection.last_sync_status = "success"
        connection.last_sync_error = None
        db.commit()
        return {"project_id": project_id, "status": "success", "mailbox": connected_email,
                "messages_scanned": scanned, "documents_added": ingested,
                "keyword_count": len(keywords), "next_sync_minutes": connection.interval_minutes}
    except Exception as exc:
        db.rollback()
        current = db.query(EmailSyncConnection).filter(EmailSyncConnection.project_id == project_id).first()
        if current:
            current.last_sync_status = "error"
            current.last_sync_error = f"{type(exc).__name__}: {str(exc)[:800]}"
            db.commit()
        raise


def sync_enabled_projects() -> None:
    db = SessionLocal()
    try:
        connections = db.query(EmailSyncConnection).filter(EmailSyncConnection.sync_enabled.is_(True)).all()
        for connection in connections:
            # Scheduler checks each connection at its own configured interval.
            last = connection.last_attempt_at or connection.last_success_at
            interval = max(15, min(1440, int(connection.interval_minutes or DEFAULT_INTERVAL_MINUTES)))
            if last and (datetime.utcnow() - last) < timedelta(minutes=interval):
                continue
            project_id = connection.project_id
            try:
                sync_project_emails(db, project_id)
            except Exception as exc:
                print(f"Outlook scheduled sync failed for {project_id}: {type(exc).__name__}: {exc}")
                db.rollback()
    finally:
        db.close()
