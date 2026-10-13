from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from app.core.database import Base


class RelayIntelligenceRecord(Base):
    """Stored change investigations and their human-reported outcomes."""

    __tablename__ = "relay_intelligence_records"

    record_id = Column(String(32), primary_key=True)
    project_id = Column(
        String(64),
        ForeignKey("relay_projects.project_id"),
        nullable=False,
        index=True,
    )
    record_type = Column(String(40), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False)
    outcome_status = Column(String(32), nullable=True)
    outcome_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    outcome_recorded_at = Column(DateTime, nullable=True)
