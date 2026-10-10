"""Synthetic additional Relay demo records. All dates are demo planning dates."""
from datetime import date

ADDITIONAL_PROJECTS = [
    {"project_id": "PROJ-002", "name": "Customer Data Migration", "status": "At Risk", "planned_release": date(2026, 10, 28), "risk_score": 68, "is_synthetic": True},
    {"project_id": "PROJ-003", "name": "Analytics Modernization", "status": "Delayed", "planned_release": date(2026, 11, 6), "risk_score": 74, "is_synthetic": True},
]

ADDITIONAL_TASKS = [
    {"task_id": "TASK-201", "project_id": "PROJ-002", "name": "Source data profiling", "status": "Delayed", "planned_date": date(2026, 10, 10), "forecast_date": date(2026, 10, 13), "owner": "Data Engineering"},
    {"task_id": "TASK-202", "project_id": "PROJ-002", "name": "Data cleansing and mapping", "status": "Blocked", "planned_date": date(2026, 10, 14), "forecast_date": date(2026, 10, 18), "owner": "Migration Team"},
    {"task_id": "TASK-203", "project_id": "PROJ-002", "name": "Migration rehearsal", "status": "At Risk", "planned_date": date(2026, 10, 20), "forecast_date": date(2026, 10, 23), "owner": "Platform Team"},
    {"task_id": "TASK-204", "project_id": "PROJ-002", "name": "Business sign-off", "status": "Not Started", "planned_date": date(2026, 10, 25), "forecast_date": date(2026, 10, 27), "owner": "Business Operations"},
    {"task_id": "TASK-205", "project_id": "PROJ-002", "name": "Production migration", "status": "At Risk", "planned_date": date(2026, 10, 28), "forecast_date": date(2026, 10, 30), "owner": "Release Team"},
    {"task_id": "TASK-301", "project_id": "PROJ-003", "name": "Source pipeline configuration", "status": "Delayed", "planned_date": date(2026, 10, 12), "forecast_date": date(2026, 10, 16), "owner": "Data Platform Team"},
    {"task_id": "TASK-302", "project_id": "PROJ-003", "name": "Data model validation", "status": "Blocked", "planned_date": date(2026, 10, 17), "forecast_date": date(2026, 10, 21), "owner": "Analytics Engineering"},
    {"task_id": "TASK-303", "project_id": "PROJ-003", "name": "Dashboard development", "status": "At Risk", "planned_date": date(2026, 10, 22), "forecast_date": date(2026, 10, 26), "owner": "BI Team"},
    {"task_id": "TASK-304", "project_id": "PROJ-003", "name": "Stakeholder acceptance testing", "status": "Not Started", "planned_date": date(2026, 10, 29), "forecast_date": date(2026, 11, 3), "owner": "Business Analytics"},
    {"task_id": "TASK-305", "project_id": "PROJ-003", "name": "Analytics rollout", "status": "At Risk", "planned_date": date(2026, 11, 6), "forecast_date": date(2026, 11, 10), "owner": "Release Team"},
]

ADDITIONAL_DEPENDENCIES = [
    {"task_id": "TASK-202", "depends_on_task_id": "TASK-201"},
    {"task_id": "TASK-203", "depends_on_task_id": "TASK-202"},
    {"task_id": "TASK-204", "depends_on_task_id": "TASK-203"},
    {"task_id": "TASK-205", "depends_on_task_id": "TASK-204"},
    {"task_id": "TASK-302", "depends_on_task_id": "TASK-301"},
    {"task_id": "TASK-303", "depends_on_task_id": "TASK-302"},
    {"task_id": "TASK-304", "depends_on_task_id": "TASK-303"},
    {"task_id": "TASK-305", "depends_on_task_id": "TASK-304"},
]

ADDITIONAL_DOCUMENTS = [
    {"document_id": "DOC-201", "project_id": "PROJ-002", "title": "Data quality review", "source": "Migration team email (synthetic demo data)", "content": "Source data profiling found inconsistent customer identifiers and missing address fields. Data cleansing and mapping cannot be signed off until exceptions are reviewed.", "related_task_id": "TASK-201", "is_synthetic": True},
    {"document_id": "DOC-202", "project_id": "PROJ-002", "title": "Migration rehearsal dependency", "source": "Migration plan (synthetic demo data)", "content": "The migration rehearsal depends on approved mappings and a completed cleansing run. Business sign-off is required before production migration.", "related_task_id": "TASK-203", "is_synthetic": True},
    {"document_id": "DOC-203", "project_id": "PROJ-002", "title": "Business readiness update", "source": "Business operations update (synthetic demo data)", "content": "Business users need a reconciliation report from the rehearsal before they can approve the migration window.", "related_task_id": "TASK-204", "is_synthetic": True},
    {"document_id": "DOC-301", "project_id": "PROJ-003", "title": "Data pipeline environment blocker", "source": "Platform team email (synthetic demo data)", "content": "Source pipeline configuration is delayed while service-account permissions and the test dataset are finalized. Data model validation is waiting for a successful pipeline run.", "related_task_id": "TASK-301", "is_synthetic": True},
    {"document_id": "DOC-302", "project_id": "PROJ-003", "title": "Analytics model acceptance criteria", "source": "Analytics design note (synthetic demo data)", "content": "Dashboard development depends on validated source mappings and reconciled totals. Stakeholder acceptance testing must complete before analytics rollout.", "related_task_id": "TASK-302", "is_synthetic": True},
    {"document_id": "DOC-303", "project_id": "PROJ-003", "title": "Reporting stakeholder update", "source": "Stakeholder email (synthetic demo data)", "content": "Business stakeholders require validated metrics and sample dashboards before accepting the new analytics experience.", "related_task_id": "TASK-304", "is_synthetic": True},
]
