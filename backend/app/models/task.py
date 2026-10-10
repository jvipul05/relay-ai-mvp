from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint
from app.core.database import Base

class ProjectTask(Base):
    __tablename__ = "relay_project_tasks"
    task_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("relay_projects.project_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(64), nullable=False)
    planned_date = Column(Date, nullable=False)
    forecast_date = Column(Date, nullable=False)
    owner = Column(String(255), nullable=False)

class TaskDependency(Base):
    __tablename__ = "relay_task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id", name="uq_relay_task_dependency"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("relay_project_tasks.task_id"), nullable=False, index=True)
    depends_on_task_id = Column(String(64), ForeignKey("relay_project_tasks.task_id"), nullable=False, index=True)
