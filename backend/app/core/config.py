"""Environment-backed application settings. Never commit secrets to source control."""
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Relay AI")
APP_VERSION = os.getenv("APP_VERSION", "0.3.0")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]


def database_url() -> str:
    """Allow DATABASE_URL for tests/deployment; otherwise build a MySQL URL safely."""
    override = os.getenv("DATABASE_URL")
    if override:
        return override

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing database settings in backend/.env: " + ", ".join(missing)
        )

    from sqlalchemy.engine import URL

    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME"),
    ).render_as_string(hide_password=False)
