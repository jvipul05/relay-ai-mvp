"""Environment-backed application settings. Never commit secrets to source control."""
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Relay AI")
APP_VERSION = os.getenv("APP_VERSION", "0.4.0")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


# Safe default for the shared hackathon environment: no real mailbox access.
PUBLIC_DEMO_MODE = _read_bool("RELAY_PUBLIC_DEMO_MODE", True)
GMAIL_CONNECTOR_ENABLED = not PUBLIC_DEMO_MODE and _read_bool("RELAY_ENABLE_GMAIL_CONNECTOR", False)
ENABLE_IN_PROCESS_SCHEDULER = (
    not PUBLIC_DEMO_MODE and GMAIL_CONNECTOR_ENABLED
    and _read_bool("RELAY_ENABLE_IN_PROCESS_SCHEDULER", False)
)
# Per-process abuse/cost guardrails only; not production-grade distributed protection.
RATE_LIMIT_PER_MINUTE = _read_int("RELAY_RATE_LIMIT_PER_MINUTE", 120)
AI_RATE_LIMIT_PER_MINUTE = _read_int("RELAY_AI_RATE_LIMIT_PER_MINUTE", 12)


def database_url() -> str:
    """Allow DATABASE_URL for tests/deployment; otherwise build a MySQL URL safely."""
    override = os.getenv("DATABASE_URL")
    if override:
        return override

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing database settings in backend/.env: " + ", ".join(missing))

    from sqlalchemy.engine import URL

    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME"),
    ).render_as_string(hide_password=False)
