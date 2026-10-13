from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from app.core.database import Base


class ProjectConnectorConfig(Base):
    """Project-scoped destination URLs for safe synthetic Jira/Confluence testing."""
    __tablename__ = "relay_project_connector_configs"

    project_id = Column(String(64), ForeignKey("relay_projects.project_id", ondelete="CASCADE"), primary_key=True)
    provider = Column(String(32), primary_key=True)
    base_url = Column(String(500), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
