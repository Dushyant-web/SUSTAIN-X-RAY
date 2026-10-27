# Hardware integration boundary

`backend/app/integrations.py` defines a MeterAdapter protocol (`health`, `fetch`) and an explicitly unconfigured adapter. No polling, device credentials, vendor API, Modbus registers, pulse factors, real-time capability, TDS sensor, pressure sensor or tank level sensor is assumed to exist.

Commissioning requires a physical inventory and permission to inspect: meter make/model/serial, measured stream and location, protocol/export interface, manufacturer documentation, units, scale factors, counter rollover/reset behavior, calibration, clock/timezone, network/power constraints and upstream tank/pipe topology. Existing bill meter UPP69564 is supported by bill evidence; that does not establish its connectivity.

Implement one adapter per confirmed interface. Translate raw output into validated Reading objects, retain raw packet/export source references, enforce replay idempotency and clock/sequence checks, buffer outages and record quality flags. Use authenticated server ingestion with a dedicated service identity and rate limits. Never expose device controls or credentials to browsers. Commission adapters against fixtures and a real meter before allowing source='actual'; current manual/CSV endpoints reject that claim.

RO channels must cover raw input, product and reject over the same interval. Stored water and unmetered branches affect balances. Rejection/recovery require nonzero input and confirmed compatible units; missing input is not reconstructed from an ambiguous logbook column. Block inlet meters require separate mapping. Optional TDS/pressure/tank sensors need distinct typed models with their native units and calibration before adding analytics.
