# Relay backend — modular structure

This update separates the FastAPI API layer, database models, repositories, business services and AI adapter while preserving the existing HTTP routes and response shapes.

## Folder layout

```text
backend/
├── main.py                       # compatibility entrypoint: uvicorn main:app
├── ai_agent.py                   # KEEP your existing Gemini implementation
├── seed_demo_data.py             # idempotent synthetic data seed
├── additional_demo_data.py       # Beta and Gamma synthetic records
├── .env                          # KEEP your existing database and Gemini settings
├── .env.example                  # safe settings template; no secrets
├── requirements.txt
└── app/
    ├── main.py                   # app creation and router registration
    ├── core/config.py            # environment configuration
    ├── core/database.py          # SQLAlchemy engine/session/Base
    ├── api/                      # HTTP routes
    ├── models/                   # SQLAlchemy models
    ├── schemas/                  # Pydantic request schemas
    ├── repositories/             # database queries
    ├── services/                 # project analysis and action lifecycle
    └── ai/                       # adapter to the existing Gemini module
```

## Apply safely on Windows

1. Back up the current `backend` directory (especially `main.py`, `ai_agent.py`, and `.env`).
2. Copy the `app` folder, root `main.py`, `seed_demo_data.py`, `additional_demo_data.py`, and `requirements.txt` from this bundle into `backend`.
3. **Do not overwrite or delete your existing `ai_agent.py` or `.env`.** The AI adapter deliberately uses the existing Gemini implementation.
4. Activate the existing virtual environment and install any missing packages:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m compileall app main.py seed_demo_data.py additional_demo_data.py
```

5. Seed synthetic data (inserts only missing IDs; does not overwrite existing rows):

```powershell
python seed_demo_data.py
```

6. Start with the same command as before:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## API compatibility retained

- `GET /`, `GET /health`, `GET /health/database`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `GET /api/projects/{project_id}/investigation`
- `POST /api/projects/{project_id}/ai-investigation`
- Existing recovery-action create/list/approve/execute/verify/audit endpoints

The `GET /api/projects` payload remains `{ "count": ..., "projects": [...] }` to avoid breaking the frontend project selector.

## Engineering notes

- Recovery action state changes and their audit event are committed in the same transaction.
- Action IDs are random unique IDs instead of a race-prone `MAX(id)+1` calculation.
- `Base.metadata.create_all()` remains as a safe missing-table bootstrap for this MVP; it does not drop tables. Before shared/staging/prod deployments, add Alembic migrations and use reviewed migration scripts instead of relying on `create_all()` for schema evolution.
- `DATABASE_URL` is an optional override, useful for isolated local tests. Existing `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` remain supported.
- Do not expose database credentials or Gemini API keys in frontend code, logs, or committed files.
- Recovery execution is still simulated and does not modify external systems.
