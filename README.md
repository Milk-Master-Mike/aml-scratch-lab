# AML ScratchLab

**Synthetic AML Control Testing, Investigation & Evidence Platform**

ScratchLab creates deterministic synthetic banking activity, injects known scenarios,
evaluates version-controlled monitoring controls, and proves expected-versus-actual
behavior with reproducible evidence.

> All customers and transactions are synthetic. Demonstration controls do not represent
> proprietary bank rules. ScratchLab assists control testing and does not determine
> criminality.

## Milestone 3

ScratchLab is now a complete local control-testing and alert-enrichment platform:

- Seeded synthetic customers, accounts, and 30/60/90-day transaction baselines
- 16 deterministic scenarios with paired alert and no-alert coverage
- Seven validated YAML controls covering rapid movement, velocity, volume deviation,
  funnel activity, circular flow, dormant activation, and profile mismatch
- Immutable control-version snapshots and runtime enable/disable toggles
- Run-all regression batches with PASS, FAIL, UNTESTED, and coverage summaries
- An ephemeral intentional-regression demo that never modifies active controls
- PostgreSQL persistence for bank data, alerts, and test evidence
- FastAPI scenario and test-run endpoints
- A dark analyst UI for scenario forging, the scenario library, control management,
  and regression analysis
- Automatic alert enrichment with internal evidence, OFAC screening, mapped FinCEN
  intelligence, and deterministic fictional adverse media
- Normalized, timestamped evidence packets with isolated per-source failure handling
- Pinned public-source subsets with provenance and integrity checks for offline demos
- An evidence panel in Scenario Forge that preserves human-review language

## Run locally

```bash
docker compose up --build
```

Open [ScratchLab](http://localhost:3000) or the [API documentation](http://localhost:8000/docs).
Use **Scenario Forge** for individual tests or **Regression Runner** for the complete suite.
The intentional-regression action changes `AML-RMF-001` only in memory for one batch,
proves that the rapid-movement scenario fails, and leaves the active definition untouched.

## API highlights

- `GET /api/v1/scenarios`
- `GET /api/v1/controls`
- `PATCH /api/v1/controls/{control_id}`
- `POST /api/v1/regression-runs`
- `POST /api/v1/regression-runs/intentional-regression`
- `GET /api/v1/regression-runs/{batch_id}`
- `GET /api/v1/alerts/{alert_id}/evidence`

## Test

```bash
python -m pip install -e '.[dev]'
python -m pytest

cd apps/web
npm ci
npm test
npm run build
```

## Reproducibility boundary

The seed controls IDs, names, accounts, transaction amounts, and simulation timestamps.
Execution timestamps and test-run IDs are operational metadata and intentionally vary.
`scenario_id` is retained for the assertion harness but removed from the monitoring
engine's transaction view.

The bundled OFAC data is a curated demonstration subset, not a complete screening list.
Mock adverse-media records are entirely fictional. Candidate matches always require human review.

## Architecture

```text
Next.js testing workspaces → FastAPI → deterministic scenario library
                                         ↓
                               typed YAML control dispatch
                                         ↓
                      PostgreSQL versions, batches, evidence, results
```
