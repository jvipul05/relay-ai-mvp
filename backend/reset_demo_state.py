"""Reset generated action/Ripple history for a disposable Relay demo database.

Project, task, dependency and document records are preserved.
"""
import argparse
import os
import sys

from app.core.database import Base, SessionLocal, engine
from app import models  # noqa: F401 - register SQLAlchemy metadata
from app.models.action import ActionAudit, RecoveryAction
from app.models.intelligence import RelayIntelligenceRecord


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-demo-reset", action="store_true",
                        help="Confirm deletion of action/audit/Ripple workflow history.")
    args = parser.parse_args()
    if not args.confirm_demo_reset:
        parser.error("No data changed. Add --confirm-demo-reset after verifying DATABASE_URL.")

    if engine.url.get_backend_name() != "sqlite" and os.getenv(
        "RELAY_ALLOW_NON_SQLITE_DEMO_RESET", ""
    ).strip().lower() not in {"1", "true", "yes"}:
        print("Refusing to reset a non-SQLite database. Set RELAY_ALLOW_NON_SQLITE_DEMO_RESET=true "
              "only for a disposable demo database.", file=sys.stderr)
        return 2

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        audit_count = db.query(ActionAudit).delete(synchronize_session=False)
        action_count = db.query(RecoveryAction).delete(synchronize_session=False)
        ripple_count = db.query(RelayIntelligenceRecord).delete(synchronize_session=False)
        db.commit()
        print(f"Demo history reset: {action_count} actions, {audit_count} audit events, "
              f"{ripple_count} Ripple records removed. Projects/tasks/documents preserved.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
