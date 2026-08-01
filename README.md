# InvoiceX

InvoiceX uses a Firebase-first backend:

- Cloud Firestore stores invoice, analysis, verification, and settlement state.
- Cloud Storage for Firebase stores uploaded transaction evidence.
- Firebase Security Rules deny direct client access; the FastAPI API is the
  trusted data boundary for the current MVP.
- Local development and deterministic tests keep an explicit in-memory/local
  storage mode.

Firebase Authentication will be connected when the account and role contract is
implemented. It is intentionally not simulated with ad-hoc headers.
