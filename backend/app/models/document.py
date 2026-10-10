from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from app.core.database import Base

class ProjectDocument(Base):
    __tablename__ = "relay_project_documents"
    document_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("relay_projects.project_id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    related_task_id = Column(String(64), ForeignKey("relay_project_tasks.task_id"), nullable=True, index=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
