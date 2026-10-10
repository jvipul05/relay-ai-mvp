from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.core.database import Base

class RecoveryAction(Base):
    __tablename__ = "relay_recovery_actions"
    action_id = Column(String(32), primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending_approval")
    created_at = Column(DateTime, nullable=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    execution_result = Column(Text, nullable=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_result = Column(Text, nullable=True)

class ActionAudit(Base):
    __tablename__ = "relay_action_audit"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(32), ForeignKey("relay_recovery_actions.action_id"), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    actor = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
