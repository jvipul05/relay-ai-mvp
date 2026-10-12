# Relay background sync on Cloud Run

Relay currently supports project-scoped Gmail sync. For local development, APScheduler may run
inside FastAPI. For Cloud Run, use a one-shot **Cloud Run Job** triggered by **Cloud Scheduler**
so sync continues independently of web request traffic and scale-to-zero.

## One-time setup (PowerShell)

These commands use the existing project, service account and Secret Manager names. They create
one Cloud Run Job and one Scheduler job; Google Cloud usage can incur charges beyond free quotas.

```powershell
$project = "relay-ai-mvp-vj-2026"
$region = "asia-south1"
$service = "relay-backend"
$runtimeSa = "relay-runner@relay-ai-mvp-vj-2026.iam.gserviceaccount.com"
$backendImage = gcloud run services describe $service --project $project --region $region --format="value(spec.template.spec.containers[0].image)"

if (-not $backendImage) { throw "Could not find the current relay-backend image. Deploy the backend first." }

gcloud run jobs create relay-sync-job `
  --project $project `
  --region $region `
  --image $backendImage `
  --command python `
  --args "-m,app.workers.sync_once" `
  --service-account $runtimeSa `
  --set-secrets "/secrets/env/.env=relay-backend-env:latest,/secrets/oauth/client_secret.json=relay-oauth-client:latest" `
  --set-env-vars "GOOGLE_OAUTH_CLIENT_FILE=/secrets/oauth/client_secret.json" `
  --tasks 1 `
  --max-retries 1 `
  --task-timeout 300s

gcloud run jobs add-iam-policy-binding relay-sync-job `
  --project $project `
  --region $region `
  --member "serviceAccount:$runtimeSa" `
  --role roles/run.invoker

$runJobUri = "https://$region-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$project/jobs/relay-sync-job:run"

gcloud scheduler jobs create http relay-sync-every-15-min `
  --project $project `
  --location $region `
  --schedule "*/15 * * * *" `
  --time-zone "UTC" `
  --uri $runJobUri `
  --http-method POST `
  --oauth-service-account $runtimeSa `
  --message-body "{}" `
  --attempt-deadline 320s
```

Run the job once manually and check its execution logs before disabling the in-process scheduler:

```powershell
gcloud run jobs execute relay-sync-job --project $project --region $region --wait
gcloud run services update relay-backend --project $project --region $region --update-env-vars RELAY_ENABLE_IN_PROCESS_SCHEDULER=false
```

Do not set `RELAY_ENABLE_IN_PROCESS_SCHEDULER=false` until the job and Scheduler trigger are
created and verified. The existing FastAPI routes for manual Gmail sync remain available.

## Notes

- The job uses the same Secret Manager mounts as the backend; secrets are not copied into code.
- Email sync is read-only and project-keyword scoped.
- The application enforces a minimum 15-minute interval per project's Gmail config.
- The Cloud Scheduler job only triggers one pass; the worker skips projects that are not due.
- Check Cloud Run Job execution logs and the Gmail status endpoint after a failed run.
- Keep `--max` and request concurrency on the web service conservative while the MySQL pool is
  limited. Add Cloud Tasks later if Relay introduces long-running file ingestion or user-triggered
  tasks that need durable per-request retries.
