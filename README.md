# Relay AI — Organizational Intelligence for the Future of Work

**Turn a small work signal into an evidence-backed map of portfolio impact, then help a human approve and verify the recovery plan.**

Relay is an AI decision-support teammate for project and operations teams. It connects fragmented delivery evidence to downstream impact, makes trade-offs visible, and turns recommendations into accountable work without pretending that an AI suggestion is an approved decision.

## Why it matters for the Future of Work

Modern work is asynchronous and cross-functional: an update in one team, supplier, or project can quietly affect release plans elsewhere. Teams often spend time reconciling emails, plans, blockers, and owners before deciding what to do. A general-purpose copilot can summarize a message, but it often stops before mapping portfolio impact and supporting a controlled follow-through.

Relay focuses on the work between **signal → shared understanding → decision → accountable action**.

## End-to-end demo

1. **Detect a change.** Select a project and paste a vendor update, meeting decision, requirement change, or operational signal into Ripple Intelligence.
2. **Trace impact.** Relay retrieves project evidence and combines Gemini structured analysis with project/task/dependency/resource context. Results include uncertainty and missing information where available.
3. **Compare possible futures.** Inspect “what-if” scenarios, projected release slips, risk indices, assumptions, and trade-offs. The risk index is illustrative—not a probability or calibrated forecast.
4. **Turn a recommendation into work.** Send an intervention to Recovery Actions. It starts in **Pending approval** and carries the rationale, trade-offs, signal, investigation ID, and evidence references.
5. **Close the loop.** Approve, run the simulated execution, verify the outcome, and inspect the audit trail. No external work system is changed by this simulation.

## What is included

- Portfolio overview and project creation with starter tasks and a searchable project brief.
- Deterministic project investigation plus Gemini-assisted investigation.
- Retrieval-augmented project chat and evidence search with source references.
- Ripple Intelligence: change classification, cross-project impact, contradiction/trust checks, assumptions, scenario comparison, history, and human outcome feedback.
- Relay Studio: text/image/audio input, user-provided JSON Schema, structured output, optional Google Search grounding, and destination-shaped Jira/Confluence/Slack previews.
- Recovery Actions: pending approval → approved → simulated execution → verified, with an inspectable audit timeline.
- Synthetic Jira and Confluence previews for repeatable demonstrations; these do **not** call Atlassian APIs.
- Gmail read-only integration code for private deployments. It is disabled by default in public-demo mode.
- Request timing, AI-stage timing, embedding reuse/caching, lazy-loaded frontend pages, and CI checks.

## Architecture

```text
React + Vite
    │  REST / JSON
    ▼
FastAPI ── Gemini structured reasoning
    │      RAG retrieval (embeddings + keyword fallback)
    │      explicit rule-based scenario simulator
    ▼
SQLAlchemy ── SQLite for local demo / configured SQL database for deployment
    │
    ├── project, task, dependency and evidence records
    ├── Ripple investigation and outcome history
    └── recovery action state + audit events
```

The AI proposes interpretations and options; application code handles validation, retrieval, workflow state transitions, and audit persistence. Human approval remains explicit. “Execute simulation” is intentionally non-destructive.

## Run locally

Requirements: Python 3.12+, Node.js 22+, and a Gemini API key for AI features.

### 1. Start the backend

In PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set `GEMINI_API_KEY`. The example uses a local SQLite database, so you do not need MySQL for a local demo.

Then run the repeatable seed and API:

```powershell
python seed_demo_data.py
uvicorn app.main:app --reload
```

The API is available at http://127.0.0.1:8000 and interactive API docs at http://127.0.0.1:8000/docs.

### 2. Start the frontend

In a second terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:5173. The frontend defaults to `http://127.0.0.1:8000`; update `VITE_API_BASE_URL` in `frontend/.env.local` if your backend runs elsewhere.

### Gmail connector (private deployment only)

Public-demo mode is on by default and disables Gmail OAuth/sync. To test Gmail locally with a test mailbox, set these in `backend/.env`:

```dotenv
RELAY_PUBLIC_DEMO_MODE=false
RELAY_ENABLE_GMAIL_CONNECTOR=true
RELAY_ENABLE_IN_PROCESS_SCHEDULER=false
GOOGLE_OAUTH_CLIENT_FILE=client_secret.json
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/email/gmail/callback
RELAY_TOKEN_ENCRYPTION_KEY=REPLACE_WITH_A_FERNET_KEY
```

Generate a Fernet key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Register the exact redirect URI with your Google OAuth client. Keep `client_secret.json`, tokens, and credentials private. **Do not enable Gmail on a publicly shared hackathon demo.** For scheduled production sync, use one managed scheduler/Cloud Run Job rather than starting a scheduler in every application instance; see [backend/CLOUD_RUN_JOBS.md](backend/CLOUD_RUN_JOBS.md).

## Demo reset

To clear only generated recovery-action records, action audit events, and Ripple investigation/outcome history while preserving projects, tasks, dependencies, and documents:

```powershell
cd backend
python reset_demo_state.py --confirm-demo-reset
python seed_demo_data.py
```

The reset command refuses non-SQLite databases unless `RELAY_ALLOW_NON_SQLITE_DEMO_RESET=true` is explicitly set. Use it only against a disposable demo database.

## Build and checks

```powershell
# Backend
cd backend
python -m compileall -q .
pytest -q

# Frontend (use another terminal, or return to the repository root)
cd ..\frontend
npm ci
npm run lint
npm run build
```

GitHub Actions runs backend compilation/tests and frontend lint/build on pull requests.

## Deployment checklist

- Set `CORS_ORIGINS` to the exact deployed frontend origins.
- Build the frontend with `--build-arg VITE_API_BASE_URL=https://YOUR_BACKEND_HOST`; the existing demo backend URL remains the Docker default for backward compatibility.
- Keep `RELAY_PUBLIC_DEMO_MODE=true` on a public hackathon demo. It disables real Gmail access and activates best-effort, process-local rate limits for API/AI-heavy requests.
- Use secret storage for Gemini credentials and database passwords. Never commit populated `.env` files, OAuth client JSON, or encryption keys.
- Use a managed database and explicit schema migration process for durable deployments. Current startup creates missing tables; it does not migrate existing schemas.
- The guest screen is a **UI-only demo gate**, not authentication. Public demo data is shared across visitors and the API does not yet provide authenticated tenant-isolated workspaces. Do not enter confidential data; add server-side identity, authorization, and data isolation before production use.
- The rate limiter is a prototype cost guard, not a security boundary or distributed defense. Production needs gateway-level limits, authentication, and observability.

## Responsible-AI boundaries

- Evidence references, assumptions, missing information, and trade-offs are shown where available; the model may still be wrong.
- Scenario results are illustrative calculations, not probabilities or guaranteed delivery forecasts.
- Jira/Confluence records and recovery execution are synthetic/simulated in this build.
- Gmail uses read-only scope and is disabled by default in public-demo mode.
- A production release would need authentication/authorization, tenant isolation, connector permission reviews, retention controls, calibrated evaluations, and verified integrations.

## Hackathon materials

See [HACKATHON_SUBMISSION.md](HACKATHON_SUBMISSION.md) for the Future of Work abstract, differentiators, demo narrative, and final checklist.
