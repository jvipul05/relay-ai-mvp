# Import all models before Base.metadata.create_all() or migration autogeneration.
from app.models.project import ProjectRecord
from app.models.task import ProjectTask, TaskDependency
from app.models.document import ProjectDocument
from app.models.document_chunk import DocumentChunk
from app.models.action import RecoveryAction, ActionAudit
from app.models.gmail_sync import GmailConnection, GmailOAuthState, GmailProcessedMessage, GmailSyncConfig

__all__ = [
    "ProjectRecord", "ProjectTask", "TaskDependency", "ProjectDocument",
    "DocumentChunk", "RecoveryAction", "ActionAudit", "GmailConnection",
    "GmailOAuthState", "GmailProcessedMessage", "GmailSyncConfig",
]
