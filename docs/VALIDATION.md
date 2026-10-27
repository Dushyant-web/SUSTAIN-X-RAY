# Validation record

Implementation date: 27 October 2026 (Asia/Kolkata).

- Source review: all six supplied PDFs inspected as described in SOURCE_REVIEW.md. Original bill first pages checked visually; water scans reviewed as 13-page contact sheets and first-page detail. No ambiguous water measurements imported.
- Backend: 18 pytest cases passed, covering bill math/period normalization, validation, duplicate/atomic CSV import, equivalent timestamp duplicates, cumulative deltas/reset detection, aligned/missing/zero-input water balances, thresholds, verification statuses/cost estimates, closure audit requirements, authentication/role checks and filtered reports/exports.
- Frontend: 3 Vitest formatting tests passed. TypeScript strict type check, ESLint, Python Ruff lint and Vite production build passed after the modular refactor. Vendor chunk separation keeps each generated bundle below the default 500 kB warning threshold.
- Local preview: overview, electricity, water entry dialog and generated reports inspected in the in-app browser with real API responses. Corrected August active energy and period comparisons visible. No live readings or savings shown. Browser verification is not a complete automated accessibility or mobile-device test.
- Security: local authorization bypass is explicitly labelled and opt-in via APP_MODE=local. Production defaults to Firebase token and active role validation. Direct Firestore client writes denied. Pytest checks anonymous, invalid-token, disabled-user and viewer-write rejection.
- External limits: Firestore emulator rule tests are supplied but not executed; Firebase CLI/emulator setup and a configured Firebase project were not available. Production ADC/token verification against real accounts and Firestore transport remain unverified. No Docker/Vercel/cloud deployment or hardware commissioning performed.
- Dependency setup: frontend package lock provided. Python virtual environment installed including Firebase Admin and tested successfully; one upstream Starlette/httpx deprecation warning remains. A tested dependency lock is supplied. Do not commit or ship the ignored local runtime database as a verified production source.

## Remaining MVP limitations

No independent savings audit, seasonal/weather model, scheduled notifications, automatic PDF ingestion, historical score snapshots, high-volume pagination or vendor hardware driver. Concurrent overlap preflight and ticket updates require transaction/version hardening before multi-operator production use. RO input/channel/units/interval validation and separate block evidence are required to unlock source-backed water analysis.

## Live simulator extension

23 backend tests pass, including simulator interval integration, synthetic provenance, deterministic seed, spike/balance/dropout scenarios, bounded buffers, pause/resume, isolated API storage and viewer write denial. Frontend lint, TypeScript production build and Python Ruff checks pass. Local browser verified start and streaming controls. Simulator generation is asynchronous and independent of browser polling; sample CSV export retains demo provenance. Cloud multi-worker behavior is not supported; see SIMULATOR.md.
