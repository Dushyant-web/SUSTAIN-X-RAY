# Implementation phases
1. Inspect source PDFs and document provenance, corrections and uncertainties.
2. React/Vite navigation, accessible shared forms and Firebase login; explicit local development mode.
3. Typed FastAPI models, SQLite local adapter / Firestore production adapter, atomic validated imports.
4. Electricity periods, kWh and kVAh distinctions, costs, demand and transparent comparison rules.
5. Six water categories, cumulative normalization, aligned balances and source-quality controls.
6. Persisted alerts, ticket lifecycle/audit, evidence-based verification with conservative eligibility.
7. Configurable score and hypothetical scenarios, filtered reports and CSV export.
8. Hardware contracts, security rules, tests, production build and deployment instructions.

The workspace was empty. User explicitly requests Vercel + Python backend; use that architecture, not Sites Worker hosting. No cloud deployment is attempted without target configuration. Tests and build form phase gates; external Firebase/hardware tests require configuration.
