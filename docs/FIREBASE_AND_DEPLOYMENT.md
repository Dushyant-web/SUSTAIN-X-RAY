# Firebase and deployment

## Firebase
1. Create a Firebase project, enable Firestore (native mode), and enable Email/Password in Firebase Authentication. Set allowed frontend auth domains.
2. Create the first administrator account in Authentication. In the Firestore console, create `users/<exact Firebase UID>` with `name`, `role: "admin"`, `active: true`, `created_at`, `updated_at`. Do not permit public self-assignment of roles.
3. Deploy `firestore.rules` and `firestore.indexes.json` using Firebase CLI: `firebase deploy --only firestore --project YOUR_PROJECT_ID`. Rules deny all direct client writes. Authenticated, active users can read permitted data; only admins can list other users.
4. Configure backend `APP_MODE=production`, `FIREBASE_PROJECT_ID`, Application Default Credentials (prefer workload identity), and an exact `CORS_ORIGINS` allowlist. Never put service-account JSON in the frontend, repository or build context.
5. Configure the frontend variables from `frontend/.env.example`, then rebuild. Login uses Firebase email/password and sends ID tokens to FastAPI. Backend verifies revocation, then reads active role from Firestore on every request. Viewer: read; operator: data/workflow writes; admin: settings, registry, user provisioning and source seed. Firebase Auth account creation remains in console; the app manages role profiles for existing UIDs.
6. Import the historical bills explicitly with `PYTHONPATH=backend python -m app.seed` under production credentials, or use the admin Electricity page's seed action on an empty database.

The backend Admin SDK bypasses Firestore rules. Backend role checks are therefore a required security boundary, not optional frontend controls. Do not deploy local mode. No cloud credentials were available during implementation; deployed Auth/Firestore integration and emulator security-rule execution must be tested in your configured environment.

## Vercel frontend
Import this repository into Vercel; set project root `frontend`, build `npm run build`, output `dist`, Node 22. Set `VITE_API_URL` to the HTTPS backend origin (without `/api`), and Firebase web values. `frontend/vercel.json` supplies SPA fallback. The Vite development proxy only applies locally. No deployment has been performed or claimed.

## Python backend
Use Cloud Run, Render, Fly.io or another Python container service. Build from repo root: `docker build -f backend/Dockerfile -t sustain-x-ray-api .`. Supply server environment and ADC/workload identity; route HTTPS to container port 8000. Ensure your hosting platform uses that port or overrides the command as needed. Health route `/api/health`; API docs `/docs`. Configure concurrency, rate limits and request-body limits at the edge. Use secrets manager. Firestore provides durable storage; the SQLite adapter is only for explicit local development.

## Operational limits
This is an MVP for one campus with low-volume imports (200 rows / 1 MB per CSV). Dashboard computations currently load collections; add paginated repository queries, summary snapshots, transactional overlap checks and scheduled analysis before high-volume telemetry. Imports are atomic and exact identities are unique, but interval overlap checking is an application preflight; simultaneous distinct-ID overlapping submissions need transactional range locking before concurrent production ingestion. Ticket history updates similarly require transaction/version checks for concurrent operators. Alerts are evaluated when the dashboard is read; there is no background email/SMS delivery. No external messages are sent.

Before production: run Firestore emulator tests below, check roles using separate accounts, verify backups/retention, assess campus data sharing, configure hosting/network controls, and commission real sources. Existing local data is not automatically migrated into Firestore.
