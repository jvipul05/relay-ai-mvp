"""Periodic scheduler for project-specific Outlook inbox sync."""
from apscheduler.schedulers.background import BackgroundScheduler
from app.email_sync.microsoft_graph import sync_enabled_projects

scheduler = BackgroundScheduler(timezone="UTC", daemon=True)


def start_scheduler() -> None:
    if scheduler.running:
        return
    # Poll every minute; per-project intervals (minimum 15 minutes) are enforced in sync_enabled_projects.
    scheduler.add_job(sync_enabled_projects, "interval", minutes=1, id="relay-outlook-sync",
                      replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
