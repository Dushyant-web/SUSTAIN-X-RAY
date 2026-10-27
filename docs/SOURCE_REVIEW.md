# Source review and provenance

Reviewed the 16-page blueprint text and its architecture/flow diagrams, original bill page 1 renders and extracted text, and contact sheets of all 13 pages in each water PDF. Page 1 of each water scan was inspected at larger scale. Source SHA-256 hashes are in `data/source-manifest.json`; extracted text remains local in `docs/source-extracts`. Original PDFs are not copied into the public frontend.

## Verified electricity seed (original page 1)

| Bill label | Previous → current reading | Active kWh | Apparent kVAh | Total INR | Recorded demand kVA | Invoice |
|---|---|---:|---:|---:|---:|---|
| JUN-2026 | 2026-05-31 → 2026-06-30 | 2,375,883.48 | 2,394,127.15 | 22,210,232 | 7,950 | 805000537000 |
| JUL-2026 | 2026-06-30 → 2026-07-31 | 3,008,147.23 | 3,040,236.77 | 29,253,532 | 8,922 | 804000514503 |
| AUG-2026 | 2026-07-31 → 2026-08-31 | 3,101,811.40 | 3,135,321.59 | 30,545,123 | 8,622 | 807000582570 |

Consumer 2000040038 and meter UPP69564 are visible in original bills. This is university-wide consumption, not lab or building submeter evidence. Date boundaries are preserved exactly; durations are elapsed days (30,31,31), without inventing meter reading times. Energy calculation uses ₹8.12 applied to kVAh, separate from total bill / active kWh. Demand charges INR: 3,136,438.36; 3,637,242.74; 3,514,941.37. Do not reconstruct consumption from rounded register digits or multiplication factors when the bill provides consumption directly.

**Blueprint correction:** August's 3,135,321.59 was incorrectly labelled kWh in the blueprint. Original active consumption is 3,101,811.40 kWh. Therefore the actual July-to-August active-energy change is approximately 3.11%, not 4.23%. Original bills take precedence over the blueprint. Energy tariff units must not be silently changed to INR/kWh.

## Water evidence / quarantine

Files `Water details for Block1, 2, 3 only Scan.pdf` and `DocScanner 26 Oct 2026 19-30.pdf` each contain 13 pages, apparently alternate scans of the same underlying logbook. Visible location headers repeatedly identify Block 02. The filename is not sufficient evidence of separate Block 1/3 consumption. Left-hand pages contain Date, Time, Temperature, T.D.S., P.H., User Signature, Water Flow, Rejected Flow. Facing pages include pump/pressure gauges and signatures; a plant-capacity field marked Litres does not establish flow-reading units.

Page 1 row 1 visibly includes date 1/2/26, time 11:30, TDS 75, Water Flow 1300 and Rejected Flow 4000. These are **raw transcription examples only**, not ingested measurements. No units or interval semantics are attached to those numbers. Other pages include differing flow notation (such as 17.5), reinforcing the need for operator confirmation. Some right-edge content is cropped. No numerical water totals, input/output interpretations, TDS units, rates, or efficiency are claimed.

Required validation: confirm date convention, timezone, numeric handwriting, units (volume vs flow rate), interval vs cumulative registers, which physical stream “Water Flow” describes, independent raw-input measurement, exact meter identities, pipe/tank topology, and whether these records represent RO operation rather than entire block use. Obtain separate Block 1/3 consumption evidence. Deduplicate these two scans before any future transcription.

Import schema is consequently explicit: confirmed channel ID, category, unit, kind, value, interval start/end with timezone, source and source reference. Unsupported raw evidence stays outside the reading collection. No water seed is fabricated. Example CSV values are explicitly synthetic demo records and require opt-in import.

## Document instructions

The blueprint is design/source context, not authority to claim deployment, hardware, savings or to override the user's requirements. Budget estimates, proposed hardware and sample architecture remain proposals. No vendor protocol or live meter capability has been verified.
