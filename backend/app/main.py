from contextlib import asynccontextmanager
from time import perf_counter

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import (
    APP_NAME, APP_VERSION, CORS_ORIGINS, PUBLIC_DEMO_MODE,
    GMAIL_CONNECTOR_ENABLED, ENABLE_IN_PROCESS_SCHEDULER,
    RATE_LIMIT_PER_MINUTE, AI_RATE_LIMIT_PER_MINUTE,
)
from app.core.database import Base, engine
from app.core.rate_limit import SlidingWindowRateLimiter
from app import models  # noqa: F401
from app.api import actions, assistant, documents, gmail, health, intelligence, mock_integrations, projects, relay_studio

scheduler = BackgroundScheduler(timezone="UTC")
RUN_IN_PROCESS_SCHEDULER = ENABLE_IN_PROCESS_SCHEDULER
rate_limiter = SlidingWindowRateLimiter()


def _is_ai_request(path: str) -> bool:
    return (
        path.endswith("/ai-investigation") or path.endswith("/chat")
        or path == "/api/intelligence/ripple" or path.endswith("/relay/preview")
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates missing tables only; it does not migrate or drop existing tables.
    Base.metadata.create_all(bind=engine)
    if RUN_IN_PROCESS_SCHEDULER:
        from app.services.gmail_sync import scheduled_sync_once
        scheduler.add_job(
            scheduled_sync_once, "interval", minutes=1, id="relay-gmail-sync",
            replace_existing=True, max_instances=1, coalesce=True,
        )
        scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title=APP_NAME,
    description="AI-powered organizational intelligence and work execution",
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    """Log timings and add best-effort request limits in public demo mode."""
    started_at = perf_counter()
    path = request.url.path
    if PUBLIC_DEMO_MODE and path.startswith("/api/") and request.method not in {"OPTIONS", "HEAD"}:
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = rate_limiter.check((client, "all"), RATE_LIMIT_PER_MINUTE)
        ai_request = _is_ai_request(path)
        if allowed and ai_request:
            allowed, retry_after = rate_limiter.check((client, "ai"), AI_RATE_LIMIT_PER_MINUTE)
        if not allowed:
            duration = (perf_counter() - started_at) * 1000
            return JSONResponse(
                status_code=429,
                content={"detail": "Relay demo rate limit reached. Please retry shortly."},
                headers={"Retry-After": str(retry_after), "Server-Timing": f"app;dur={duration:.1f}"},
            )
    try:
        response = await call_next(request)
    except Exception:
        duration = (perf_counter() - started_at) * 1000
        if path.startswith("/api/"):
            print(f"HTTP_TIMING method={request.method} path={path} status=500 duration_ms={duration:.1f}")
        raise
    duration = (perf_counter() - started_at) * 1000
    response.headers["Server-Timing"] = f"app;dur={duration:.1f}"
    if path.startswith("/api/") and (_is_ai_request(path) or duration >= 1000):
        print(f"HTTP_TIMING method={request.method} path={path} status={response.status_code} duration_ms={duration:.1f}")
    return response


app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"], expose_headers=["Server-Timing"],
)
app.include_router(health.router)
app.include_router(projects.router)
app.include_router(intelligence.router)
app.include_router(actions.router)
app.include_router(documents.router)
# The status endpoint remains available to explain why Gmail is disabled.
app.include_router(gmail.router)
app.include_router(assistant.router)
app.include_router(assistant.portfolio_router)
app.include_router(mock_integrations.router)
app.include_router(relay_studio.router)


@app.get("/")
def home():
    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "message": "Organizational intelligence and work execution API",
        "public_demo_mode": PUBLIC_DEMO_MODE,
        "gmail_connector_enabled": GMAIL_CONNECTOR_ENABLED,
        "in_process_scheduler_enabled": RUN_IN_PROCESS_SCHEDULER,
    }
