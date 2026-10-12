"""Run one scheduled Gmail sync pass and exit with a non-zero code on failures.

For Cloud Run Jobs, mount the same Secret Manager environment file at
/secrets/env/.env and the OAuth client JSON at /secrets/oauth/client_secret.json.
"""
import json
import sys
from dotenv import load_dotenv

# Load deployed secrets before importing application modules that create the DB engine.
load_dotenv("/secrets/env/.env")
load_dotenv()

from app.services.gmail_sync import scheduled_sync_once  # noqa: E402


def main() -> int:
    summary = scheduled_sync_once()
    print(json.dumps(summary, ensure_ascii=False))
    if summary.get("failures"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
