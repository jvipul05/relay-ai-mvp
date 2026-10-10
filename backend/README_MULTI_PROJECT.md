# Relay Phase 1: Multi-project seed update

This update preserves Project Alpha and adds two synthetic projects:

- `PROJ-002` — Customer Data Migration
- `PROJ-003` — Analytics Modernization

Each new project has five tasks, a dependency chain and three synthetic evidence documents. The seed inserts only missing IDs; it does not delete or overwrite existing rows. The investigation baseline is now project-agnostic rather than assuming every project contains `TASK-101`.

## Apply on Windows

1. Back up your existing `backend/main.py` and `backend/seed_demo_data.py`.
2. Copy `main.py`, `seed_demo_data.py`, and `additional_demo_data.py` from this bundle into `backend/`. Keep `.env` unchanged.
3. In PowerShell:

```powershell
cd C:\Users\jvipu\relay-ai-mvp\backend
.\.venv\Scripts\Activate.ps1
python -m py_compile main.py seed_demo_data.py additional_demo_data.py
python seed_demo_data.py
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

4. Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/projects | ConvertTo-Json -Depth 5
Invoke-RestMethod http://127.0.0.1:8000/api/projects/PROJ-002 | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8000/api/projects/PROJ-003/investigation | ConvertTo-Json -Depth 8
```

The modular frontend project selector should read `/api/projects`, so it should show all three projects after a refresh.

## Safety and limitations

- Uses your existing local `.env`; no credentials are included.
- Does not delete or overwrite existing database rows.
- All new project records are synthetic.
- Recovery actions remain simulated.
- Private MySQL connectivity cannot be tested from this environment; run the seed locally.
