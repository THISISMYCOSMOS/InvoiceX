# GCP backend deployment

The Cloud Run path uses Cloud SQL for state, a private Cloud Storage bucket for
invoice evidence, and Secret Manager for all credentials. The API process must
never use its container filesystem as durable storage.

## Resources and service identity

Create these resources in one region (the default build substitutions use
`asia-northeast3`):

- Artifact Registry Docker repository: `invoicex`
- Cloud SQL for PostgreSQL instance and `invoicex` database
- private GCS bucket: `${PROJECT_ID}-invoicex-documents`
- user-managed Cloud Run service account: `invoicex-api`
- Secret Manager values named in `backend/src/invoicex_backend/secrets.py`

Grant the Cloud Run service account only the roles it needs:

- Secret Manager Secret Accessor for InvoiceX secrets
- Cloud SQL Client for the selected instance
- Storage Object User for the private document bucket

The Cloud Run deployment must use a user-managed service account. Do not set
`GOOGLE_APPLICATION_CREDENTIALS` or ship a service-account JSON key in the
image; Google client libraries use Cloud Run's service identity automatically.
When configuring that identity, grant Cloud Run's service agent permission to
attach and sign on behalf of it as required by the Cloud Run service-identity
guide. The deployer also needs Service Account User on this identity.

## Fixed demo data

The backend owns the three fixed demo accounts and the four Investment Criteria
buyers. They are defined in `backend/src/invoicex_backend/seed.py`:

| Role | Email | Password |
| --- | --- | --- |
| Supplier | supplier@company.com | supplier |
| Buyer | buyer@company.com | buyer |
| Investor | investor@company.com | investor |

The Investment Criteria endpoint returns Prime Mobility, Orbit Components,
Daon Logistics, and Vertex Retail. In GCP mode the frontend calls the API for
this list rather than treating the browser copy as authoritative.

## Build and deploy

1. Create the Artifact Registry repository, GCS bucket, Cloud SQL instance,
   database, application user, and the secrets above.
2. Grant the service-account permissions listed above.
3. Run Cloud Build from the repository root. `cloudbuild.yaml` builds
   `backend/Dockerfile`, deploys Cloud Run with the GCP-only backend settings,
   and injects the sensitive settings from Secret Manager.

`DEPLOYMENT_TARGET=gcp` fails startup unless both `PERSISTENCE_BACKEND=cloud_sql`
and `DOCUMENT_STORAGE_BACKEND=gcs` are selected and all required values exist.
The service currently holds active workflow state in process memory, so the
deployment pins Cloud Run to one request at a time and one instance. Before
raising either limit, move the remaining workflow lock/queue state into Cloud
SQL and Cloud Tasks.

## Document security

Original PDFs and images are written beneath
`invoices/{invoice_id}/{document_id}/` in the private bucket. Cloud SQL stores
the stable `gs://` object reference; the API produces a short-lived signed URL
only when it returns an invoice. Do not make the bucket public or persist a
signed URL in the database.
