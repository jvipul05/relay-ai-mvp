"""One-time backfill: link existing Gmail documents to clearly matching project tasks."""
import re
from app.core.database import SessionLocal
from app.models import ProjectDocument, ProjectTask

STOP_WORDS = {"the", "and", "for", "from", "with", "until", "that", "this", "task", "project"}


def match_task(tasks, content):
    lowered = (content or "").lower()
    for task in tasks:
        if task.task_id and task.task_id.lower() in lowered:
            return task.task_id
    content_tokens = set(re.findall(r"[a-z0-9]+", lowered))
    best_id, best_score = None, 0
    for task in tasks:
        tokens = {t for t in re.findall(r"[a-z0-9]+", (task.name or "").lower()) if len(t) >= 3 and t not in STOP_WORDS}
        score = len(tokens & content_tokens)
        if tokens and score > best_score and score >= min(2, len(tokens)):
            best_id, best_score = task.task_id, score
    return best_id


def main():
    db = SessionLocal()
    try:
        docs = db.query(ProjectDocument).filter(ProjectDocument.source.like("gmail:%")).all()
        linked = unchanged = 0
        for doc in docs:
            if doc.related_task_id:
                unchanged += 1
                continue
            tasks = db.query(ProjectTask).filter(ProjectTask.project_id == doc.project_id).all()
            task_id = match_task(tasks, f"{doc.title}\n{doc.content}")
            if task_id:
                doc.related_task_id = task_id
                linked += 1
            else:
                unchanged += 1
        db.commit()
        print(f"Gmail documents scanned: {len(docs)}")
        print(f"Documents linked to tasks: {linked}")
        print(f"Left unlinked (no confident match or already linked): {unchanged}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
