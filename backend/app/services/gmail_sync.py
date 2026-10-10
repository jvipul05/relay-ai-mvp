"""Gmail OAuth, message parsing and project-scoped sync for Relay."""
import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import GmailConnection, GmailProcessedMessage, GmailSyncConfig, ProjectRecord, ProjectTask
from app.retrieval.rag_service import ingest_document

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_CLIENT_FILE = Path(__file__).resolve().parents[2] / "client_secret.json"


def _client_file() -> Path:
    raw = os.getenv("GOOGLE_OAUTH_CLIENT_FILE", str(DEFAULT_CLIENT_FILE))
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[2] / path).resolve()
    return path


def _redirect_uri() -> str:
    return os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/api/email/gmail/callback").strip()


def _fernet() -> Fernet:
    key = os.getenv("RELAY_TOKEN_ENCRYPTION_KEY", "").strip().encode()
    if not key:
        raise RuntimeError("RELAY_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key)
    except Exception as exc:
        raise RuntimeError("RELAY_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc


def load_client_config() -> dict:
    path = _client_file()
    if not path.exists():
        raise RuntimeError(f"Google OAuth client JSON not found at {path}. Set GOOGLE_OAUTH_CLIENT_FILE.")
    data = json.loads(path.read_text(encoding="utf-8"))
    # Google downloads can be either web or installed client JSON. This connector requires a Web application client.
    if "web" not in data:
        raise RuntimeError("The downloaded OAuth JSON is not a Web application client. Create a Web application OAuth client.")
    return data


def create_flow(state: str, code_verifier: str | None = None):
    from google_auth_oauthlib.flow import Flow
    config = load_client_config()
    flow = Flow.from_client_config(
        config,
        scopes=GMAIL_SCOPES,
        state=state,
        redirect_uri=_redirect_uri(),
        code_verifier=code_verifier,
    )
    return flow


def encrypt_credentials(credentials: Credentials) -> str:
    return _fernet().encrypt(credentials.to_json().encode("utf-8")).decode("ascii")


def decrypt_credentials(value: str) -> Credentials:
    try:
        payload = _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Could not decrypt Gmail credentials. Check that RELAY_TOKEN_ENCRYPTION_KEY has not changed.") from exc
    return Credentials.from_authorized_user_info(json.loads(payload), scopes=GMAIL_SCOPES)


def get_credentials(db: Session, project_id: str) -> tuple[GmailConnection, Credentials]:
    connection = db.query(GmailConnection).filter(GmailConnection.project_id == project_id).first()
    if not connection:
        raise LookupError("Gmail is not connected for this project")
    credentials = decrypt_credentials(connection.encrypted_credentials)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        connection.encrypted_credentials = encrypt_credentials(credentials)
        db.commit()
    if not credentials.valid:
        raise RuntimeError("Gmail authorization expired or was revoked. Reconnect Gmail for this project.")
    return connection, credentials


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        elif tag in {"p", "div", "br", "li", "tr"}:
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _decode_body(data: str | None) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _walk_parts(payload: dict, collected: list[tuple[str, str]]):
    mime = payload.get("mimeType", "")
    body = payload.get("body", {}).get("data")
    if body:
        collected.append((mime, _decode_body(body)))
    for part in payload.get("parts", []) or []:
        _walk_parts(part, collected)


def _extract_body(payload: dict) -> str:
    parts: list[tuple[str, str]] = []
    _walk_parts(payload, parts)
    plain = [text for mime, text in parts if mime == "text/plain" and text.strip()]
    if plain:
        return "\n".join(plain)
    html = [text for mime, text in parts if mime == "text/html" and text.strip()]
    if html:
        parser = _HTMLText()
        parser.feed("\n".join(html))
        return re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
    return ""


def _header(headers: list[dict], name: str) -> str:
    return next((h.get("value", "") for h in headers if h.get("name", "").lower() == name.lower()), "")


def _gmail_query(keywords: list[str], last_sync_at: datetime | None) -> str:
    if not keywords:
        raise ValueError("Configure at least one project keyword before enabling Gmail sync")
    # Gmail query escaping: remove query operators/control characters from user-provided terms.
    terms = []
    for keyword in keywords[:20]:
        clean = re.sub(r'[\r\n\\"]', " ", keyword).strip()
        if clean:
            terms.append('"' + clean[:100] + '"')
    if not terms:
        raise ValueError("No valid Gmail keywords configured")
    query = "in:inbox (" + " OR ".join(terms) + ")"
    if last_sync_at:
        dt = last_sync_at.astimezone(timezone.utc) if last_sync_at.tzinfo else last_sync_at.replace(tzinfo=timezone.utc)
        query += " after:" + str(int(dt.timestamp()))
    else:
        query += " newer_than:7d"
    return query



def _match_related_task(db: Session, project_id: str, text: str) -> str | None:
    """Conservatively associate email evidence with a task using explicit IDs or task-name overlap."""
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    if not tasks:
        return None
    lowered = (text or "").lower()
    # Explicit task IDs in an email are the strongest signal.
    for task in tasks:
        if task.task_id and task.task_id.lower() in lowered:
            return task.task_id
    # Require at least two meaningful task-name tokens to avoid weak associations.
    stop_words = {"the", "and", "for", "from", "with", "until", "that", "this", "task", "project"}
    best_id, best_score = None, 0
    for task in tasks:
        tokens = {t for t in re.findall(r"[a-z0-9]+", (task.name or "").lower()) if len(t) >= 3 and t not in stop_words}
        if not tokens:
            continue
        score = len(tokens & set(re.findall(r"[a-z0-9]+", lowered)))
        if score > best_score and score >= min(2, len(tokens)):
            best_id, best_score = task.task_id, score
    return best_id


def sync_project(db: Session, project_id: str, max_messages: int = 100) -> dict:
    project = db.query(ProjectRecord).filter(ProjectRecord.project_id == project_id).first()
    if not project:
        raise LookupError("Project not found")
    config = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == project_id).first()
    if not config:
        raise LookupError("Gmail sync configuration not found")
    keywords = json.loads(config.keywords_json or "[]")
    connection, credentials = get_credentials(db, project_id)
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    query = _gmail_query(keywords, config.last_sync_at)
    response = service.users().messages().list(userId="me", q=query, maxResults=max(1, min(max_messages, 100))).execute()
    messages = response.get("messages", []) or []
    ingested = 0
    skipped = 0
    failures = []
    for item in messages:
        message_id = item.get("id")
        if not message_id:
            skipped += 1
            continue
        exists = db.query(GmailProcessedMessage).filter(
            GmailProcessedMessage.project_id == project_id,
            GmailProcessedMessage.gmail_message_id == message_id,
        ).first()
        if exists:
            skipped += 1
            continue
        try:
            message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
            payload = message.get("payload", {})
            headers = payload.get("headers", []) or []
            subject = _header(headers, "Subject") or "(no subject)"
            sender = _header(headers, "From") or "Unknown sender"
            date_header = _header(headers, "Date")
            try:
                sent_at = parsedate_to_datetime(date_header).isoformat() if date_header else "Unknown date"
            except Exception:
                sent_at = date_header or "Unknown date"
            body = _extract_body(payload).strip()
            snippet = (message.get("snippet", "") or "").strip()
            # Do not index metadata-only messages. A snippet is accepted only as a
            # fallback when Gmail supplies meaningful message text.
            message_text = body or snippet
            if len(message_text) < 20 or not re.search(r"[A-Za-z0-9]{3,}", message_text):
                skipped += 1
                continue
            content = f"Email subject: {subject}\nFrom: {sender}\nDate: {sent_at}\nGmail message ID: {message_id}\n\n{message_text}".strip()
            related_task_id = _match_related_task(db, project_id, f"{subject}\n{message_text}")
            # Keep each message project-scoped; no attachments are fetched in this first iteration.
            result = ingest_document(
                db, project_id,
                title=f"Email: {subject}"[:255],
                source=f"gmail:{message_id}",
                content=content[:100000],
                related_task_id=related_task_id,
                is_synthetic=False,
            )
            db.add(GmailProcessedMessage(project_id=project_id, gmail_message_id=message_id, document_id=result.get("document_id")))
            db.commit()
            ingested += 1
        except Exception as exc:
            db.rollback()
            failures.append({"message_id": message_id, "error": type(exc).__name__})
    config = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == project_id).first()
    # Keep the prior watermark if any message failed so the next run can retry it.
    if not failures:
        config.last_sync_at = datetime.now(timezone.utc)
    config.last_error = (f"{len(failures)} message(s) failed" if failures else None)
    db.commit()
    return {"project_id": project_id, "mailbox": connection.email_address, "query": query,
            "messages_matched": len(messages), "messages_ingested": ingested,
            "messages_skipped": skipped, "failures": failures[:10], "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None}


def scheduled_sync_once():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        configs = db.query(GmailSyncConfig).filter(GmailSyncConfig.enabled.is_(True)).all()
        for config in configs:
            if not db.query(GmailConnection).filter(GmailConnection.project_id == config.project_id).first():
                continue
            due = config.last_sync_at is None
            if config.last_sync_at:
                last = config.last_sync_at
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                due = now - last >= timedelta(minutes=max(15, min(config.interval_minutes, 1440)))
            if not due:
                continue
            try:
                sync_project(db, config.project_id)
            except Exception as exc:
                db.rollback()
                refreshed = db.query(GmailSyncConfig).filter(GmailSyncConfig.project_id == config.project_id).first()
                if refreshed:
                    refreshed.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                    db.commit()
    finally:
        db.close()
