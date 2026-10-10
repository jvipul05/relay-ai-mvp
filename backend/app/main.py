from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.core.database import Base, engine
# Import models so SQLAlchemy registers all metadata before create_all.
from app import models  # noqa: F401
from app.api import actions, assistant, documents, gmail, health, mock_integrations, projects

scheduler = BackgroundScheduler(timezone="UTC")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates missing tables only. It does not migrate or drop existing tables.
    Base.metadata.create_all(bind=engine)
    from app.services.gmail_sync import scheduled_sync_once
    scheduler.add_job(scheduled_sync_once, "interval", minutes=1, id="relay-gmail-sync", replace_existing=True,
                      max_instances=1, coalesce=True)
    scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)

app = FastAPI(title=APP_NAME, description="AI-powered organizational intelligence and work execution", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
app.include_router(projects.router)
app.include_router(actions.router)
app.include_router(documents.router)
app.include_router(gmail.router)
app.include_router(assistant.router)
app.include_router(assistant.portfolio_router)
app.include_router(mock_integrations.router)

@app.get("/")
def home():
    return {"application": APP_NAME, "version": APP_VERSION, "message": "Organizational intelligence and work execution API"}
