from sqlalchemy import Boolean, Column, Date, Integer, String
from app.core.database import Base

class ProjectRecord(Base):
    __tablename__ = "relay_projects"
    project_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(64), nullable=False)
    planned_release = Column(Date, nullable=False)
    risk_score = Column(Integer, nullable=False, default=0)
    is_synthetic = Column(Boolean, nullable=False, default=True)
