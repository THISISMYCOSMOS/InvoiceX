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

`auth-token-secret` must be a fresh value of at least 32 characters. The
backend refuses to start with its local-development token secret when API
authentication is enabled.

Grant the Cloud Run service account only the roles it needs:

- Secret Manager Secret Accessor for InvoiceX secrets
- Cloud SQL Client for the selected instance
- Storage Object User for the private document bucket
- Service Account Token Creator on itself, so the attached identity can sign
  short-lived Cloud Storage download URLs (`iam.serviceAccounts.signBlob`)

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

In GCP mode these fixed accounts are also enforced as role boundaries:
Supplier can create and fund invoices, Buyer can review and confirm
verifications, and Investor can manage mandates, vault deposits, the dashboard,
and Investment Criteria. Local mock mode intentionally leaves those endpoints
open so the existing browser-only flow remains usable.

## Production wallet configuration

The current GCP scope is Investor Vault automatic investment, RWA issuance, and
USDC payment to the supplier. It needs these public, non-secret environment
values:

- `PRIVY_TREASURY_WALLET_ADDRESS`: Agent Vault public address
- `PRIVY_SPONSOR_WALLET_ADDRESS`: dedicated Sponsor public address that pays
  Devnet SOL transaction fees when gasless mode is enabled

`privy-sponsor-wallet-id` stays in Secret Manager. The Sponsor wallet pays
transaction fees only; it never receives or sends the investor's USDC.

`/settlement/mock-payment` models a later receivable-repayment distribution and
is disabled in the GCP deployment. It is not part of the current automatic
investment flow, so `PRIVY_SETTLEMENT_WALLET_ID` and
`PLATFORM_FEE_WALLET_ADDRESS` are intentionally not deployment requirements.
Do not use a private key, seed phrase, or a `DEMO_` address in any setting.

## Build and deploy

1. Create the Artifact Registry repository, GCS bucket, Cloud SQL instance,
   database, application user, and the secrets above.
2. Grant the service-account permissions listed above.
3. Run Cloud Build from the repository root, supplying the exact deployed
   frontend origin. `cloudbuild.yaml` deliberately requires the
   `_FRONTEND_ORIGIN` substitution rather than falling back to a permissive
   CORS policy:

   ```bash
   gcloud builds submit --config=cloudbuild.yaml \
     --substitutions=_FRONTEND_ORIGIN=https://your-frontend.example,_IMAGE_TAG=$(git rev-parse --short HEAD),_PRIVY_TREASURY_WALLET_ADDRESS=your-public-treasury-address,_PRIVY_SPONSOR_WALLET_ADDRESS=your-public-sponsor-address
   ```

   The frontend must also be built with
   `VITE_API_BASE_URL=https://<Cloud-Run-service-url>` and
   `VITE_USE_MOCK_API=false`.

4. The Cloud Build configuration builds
   `backend/Dockerfile`, deploys Cloud Run with the GCP-only backend settings,
   and injects the sensitive settings from Secret Manager.

The service is public at the Cloud Run layer so a browser frontend can call the
fixed-account login endpoint. Every application API endpoint still requires an
InvoiceX bearer token, except `/healthz`. Cloud Run has `min-instances=0`,
`max-instances=1`, and `concurrency=1` for this phase.

`DEPLOYMENT_TARGET=gcp` fails startup unless both `PERSISTENCE_BACKEND=cloud_sql`
and `DOCUMENT_STORAGE_BACKEND=gcs` are selected and all required values exist.
The service currently holds active workflow state in process memory, so the
deployment pins Cloud Run to one request at a time and one instance. Before
raising either limit, move the remaining workflow lock/queue state into Cloud
SQL and Cloud Tasks.

## Deployed frontend demo

The React frontend is served by the separate `invoicex-web` Cloud Run service.
It uses `frontend/Dockerfile` to build Vite and Nginx to serve the resulting
single-page application, including client-side route fallbacks.

Build it with the API service URL at compile time:

```bash
gcloud builds submit --config=cloudbuild.frontend.yaml \
  --substitutions=_API_BASE_URL=https://your-api-service.run.app,_IMAGE_TAG=$(git rev-parse --short HEAD)
```

After the web service receives its HTTPS URL, configure the API's
`FRONTEND_ORIGIN` to exactly that value and redeploy/update the API. The API
currently permits one exact browser origin; do not leave `localhost` configured
for a shared or remote judging demo.

## Document security

Original PDFs and images are written beneath
`invoices/{invoice_id}/{document_id}/` in the private bucket. Cloud SQL stores
the stable `gs://` object reference; the API produces a short-lived signed URL
only when it returns an invoice. Do not make the bucket public or persist a
signed URL in the database.
