# AML ScratchLab

**Repository:** `https://github.com/Milk-Master-Mike/aml-scratch-lab.git`

**Tagline:**  
**Synthetic AML Control Testing, Investigation & Evidence Platform**

> Generate synthetic banking activity → inject known AML scenarios → test monitoring controls → investigate alerts → enrich evidence → prove PASS/FAIL.

No real customer data. No proprietary bank rules. No claim that the system determines criminality.

---

# 1. Architecture

Docker Compose + localhost is the default deployment model.

```text
                       AML SCRATCHLAB
┌─────────────────────────────────────────────────────────────┐
│                         WEB UI                              │
│                        Next.js                              │
│                                                             │
│ Dashboard │ Scenario Forge │ Cases │ Graph │ Controls       │
└────────────────────────────┬────────────────────────────────┘
                             │ REST
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       FASTAPI API                           │
│                                                             │
│ Synthetic Bank │ AML Engine │ Case Engine │ Evidence API    │
└────────┬─────────────────┬──────────────────────┬────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
┌──────────────┐    ┌──────────────┐       ┌───────────────┐
│ PostgreSQL   │    │ Scratch      │       │ Test Runner   │
│              │    │ Engine       │       │               │
│ Customers    │    │              │       │ Expected      │
│ Accounts     │    │ OFAC         │       │    vs         │
│ Transactions │    │ FinCEN       │       │ Actual        │
│ Alerts       │    │ Mock Media   │       │               │
└──────────────┘    └──────────────┘       └───────────────┘
```

## Core Stack

- **Next.js + TypeScript** — UI
- **FastAPI + Python** — AML engine, synthetic data generator, enrichment service
- **PostgreSQL** — synthetic bank, cases, controls, alerts, evidence
- **Docker Compose** — local orchestration
- **GitHub Actions** — unit, integration, and regression testing

Avoid unnecessary infrastructure in V1. The goal is one polished, reproducible application.

---

# 2. Product Flair

## ScratchLab // Financial Crime Control Center

Dark charcoal/navy analyst interface.

### Top Bar

```text
SCRATCHLAB                                      DEMO BANK // SYNTHETIC
──────────────────────────────────────────────────────────────────────

CONTROL HEALTH     OPEN CASES      TEST COVERAGE      LAST TEST RUN
     94%               17              87%              2m ago
```

### Navigation

```text
◈ Command Center
◈ Scenario Forge
◈ Transaction Monitor
◈ Alert Queue
◈ Investigations
◈ Entity Graph
◈ Control Matrix
◈ Evidence Vault
◈ Test Runs
◈ Data Sources
```

Avoid making the entire product a collection of tables. Use visual investigation tools, graphs, timelines, status indicators, and animated scenario execution.

---

# 3. Scenario Forge

The Scenario Forge is the primary demo feature.

```text
╔══════════════════════════════════════════╗
║          SCENARIO FORGE                 ║
║                                         ║
║ Scenario:  Rapid Movement of Funds      ║
║                                         ║
║ Accounts              [ 4 ]             ║
║ Transactions          [ 17 ]            ║
║ Duration              [ 3 Days ]        ║
║ Customer Risk         [ Medium ]        ║
║ Expected Control      AML-RMF-001       ║
║                                         ║
║         [ INJECT SCENARIO ]             ║
╚══════════════════════════════════════════╝
```

After injection:

```text
Synthetic Customer A
       │
       │ $──────►
       ▼
    Account 12
       │
       ├────────► Account 44
       │
       ├────────► Account 71
       │
       └────────► Account 82
```

Then:

```text
⚠ CONTROL TRIGGERED

AML-RMF-001
Rapid Movement of Funds

Expected: ALERT
Actual:   ALERT

✓ PASS
```

The user should be able to watch the synthetic activity appear and immediately see whether the monitoring control behaved as expected.

---

# 4. Synthetic Data Model

Every entity is synthetic.

## Customer

```text
Customer
├── customer_id
├── synthetic_name
├── customer_type
├── occupation/business_type
├── risk_level
├── country
├── expected_monthly_volume
├── opened_at
└── seed_id
```

## Account

```text
Account
├── account_id
├── customer_id
├── account_type
├── opened_at
├── status
└── balance
```

## Transaction

```text
Transaction
├── transaction_id
├── source_account
├── destination_account
├── amount
├── currency
├── type
├── timestamp
├── geography
└── scenario_id
```

The `scenario_id` is critical.

The test harness knows which transactions were intentionally created for a test scenario. The AML detection engine does **not** receive that answer.

That allows objective expected-vs-actual testing.

---

# 5. Scenario Library

Initial scenario library:

| Scenario | Expected |
|---|---|
| Normal payroll/customer activity | No alert |
| Abnormal transaction velocity | Alert |
| Sudden volume deviation | Alert |
| Rapid movement of funds | Alert |
| Funnel pattern | Alert |
| Circular transaction network | Alert |
| Dormant account activation | Alert |
| Profile/activity mismatch | Alert |
| Sanctions-name candidate | Alert |
| Sanctions false positive | Review / clear |
| Duplicate monitoring alert | One case |
| Missing transaction data | Control failure |
| Disabled AML control | Test failure |
| Broken enrichment source | Graceful failure |
| Legitimate high-value activity | No alert |

Use configurable synthetic thresholds. Do not copy real bank thresholds or claim the demo values represent production AML settings.

---

# 6. Controls as Code

AML monitoring controls should be version-controlled rather than buried entirely in Python.

Example:

```yaml
id: AML-RMF-001
name: Rapid Movement of Funds

enabled: true

window:
  duration: synthetic_window

conditions:
  incoming_activity: elevated
  outgoing_velocity: rapid

result:
  alert: true
  severity: high

evidence:
  - transactions
  - counterparties
  - customer_baseline
```

Stored as:

```text
controls/AML-RMF-001.yaml
```

Benefits:

- Version control
- Reproducible testing
- Easy comparison of control changes
- Clear audit trail
- Easier scenario-to-control mapping

---

# 7. Scratcher / Enrichment Engine

An AML alert triggers evidence enrichment.

```text
                ALERT
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   Internal Data       Public Data
        │                   │
 Customer Profile           ├── OFAC
 Transactions               ├── FinCEN
 Counterparties             └── Mock adverse media
 Prior alerts
        │                   │
        └─────────┬─────────┘
                  ▼
             EVIDENCE PACK
```

## Internal Sources

- Customer profile
- Account profile
- Transactions
- Counterparties
- Prior alerts
- Previous test results

## Public / Demo Sources

- OFAC sanctions data
- FinCEN advisories
- Mock adverse-media feed

The system should output:

```text
POTENTIAL MATCH
Human review required
```

Never:

```text
Money launderer
```

The application assists investigation and testing. It does not make criminal determinations.

---

# 8. FinCEN Intelligence Adapter

Build a local intelligence library that can map public AML guidance into synthetic tests.

```text
INTELLIGENCE LIBRARY

FIN-XXXX-XXXX
──────────────
Source: FinCEN
Status: Imported

Extracted concepts:
● Indicator A
● Indicator B
● Indicator C

Mapped synthetic tests:
AML-SCN-021
AML-SCN-038

Control coverage:
2 / 3
```

Long-term goal:

> Does the synthetic control library contain tests covering the publicly described indicators in a given advisory?

---

# 9. Investigation Workspace

Example case screen:

```text
CASE AML-2026-00172                  HIGH

Synthetic Customer
Blue Ridge Industrial Supply LLC

Risk score             ███████░░░  72
Control                 AML-RMF-001
Transactions            17
Related accounts        4
External entities       3

┌ TRANSACTIONS ──────┐ ┌ INVESTIGATION ─────────┐
│                    │ │                          │
│ Timeline            │ │ OFAC        ✓ Complete │
│ Amount graph        │ │ KYC         ✓ Complete │
│ Counterparties      │ │ Media       ✓ Complete │
│ Geography           │ │ Network     ✓ Complete │
│                    │ │                          │
└────────────────────┘ └──────────────────────────┘
```

Tabs:

- Overview
- Transactions
- Network
- Enrichment
- Evidence
- Test Result

---

# 10. Entity Graph

Example:

```text
                         PERSON 04
                            │
                          owns
                            │
                            ▼
                     ┌──────────────┐
                     │ COMPANY A    │
                     └──────┬───────┘
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
            ACC-01        ACC-02       ACC-03
               │                         │
               ▼                         ▼
          COMPANY B ───────────────► COMPANY C
               │
               │ possible match
               ▼
          ⚠ OFAC ENTITY
```

Features:

- Zoom
- Drag nodes
- Click node for details
- Evidence drawer
- Relationship labels
- Transaction flow direction
- Highlight control-relevant entities

---

# 11. Control Matrix

```text
                   SCENARIO COVERAGE

                  Normal  Rapid  Funnel  Circular  OFAC
AML-BASE-001         ✓
AML-RMF-001                  ✓
AML-FUN-001                         ✓
AML-CIR-001                                 ✕
AML-SAN-001                                        ✓

──────────────────────────────────────────────────────

Controls       23
Passing        21
Failing         1
Untested        1

Coverage       91.3%
```

Clicking a failed control should show:

```text
EXPECTED
AML-CIR-001 should produce HIGH alert.

ACTUAL
No alert produced.

ROOT CAUSE
Control excluded ACH transactions.

TEST RESULT
FAIL
```

---

# 12. Evidence Vault

Every run creates reproducible test evidence.

```text
TEST RUN
run_2026_08_14_001

Git commit:       ab31fd7
Dataset seed:     194028
Scenario version: AML-SCN-017@2
Control version:  AML-RMF-001@4

Expected: ALERT/HIGH
Actual:   ALERT/HIGH

Result: PASS
```

Store:

```text
Input data
Control configuration
Triggered conditions
Relevant transactions
Enrichment results
Execution timestamps
Expected result
Actual result
Application version
Dataset seed
```

The dataset seed must allow the same synthetic bank and scenario to be reproduced later.

---

# 13. Repository Structure

```text
milkmastermike/
└── aml-scratch-lab/
    │
    ├── apps/
    │   ├── web/
    │   │   └── Next.js UI
    │   │
    │   └── api/
    │       └── FastAPI
    │
    ├── engine/
    │   ├── aml/
    │   ├── scenarios/
    │   ├── synthetic/
    │   ├── matching/
    │   ├── enrichment/
    │   └── evidence/
    │
    ├── controls/
    │   ├── AML-RMF-001.yaml
    │   ├── AML-FUN-001.yaml
    │   └── ...
    │
    ├── scenarios/
    │   ├── normal/
    │   ├── rapid-movement/
    │   ├── funnel/
    │   ├── circular/
    │   └── sanctions/
    │
    ├── integrations/
    │   ├── ofac/
    │   ├── fincen/
    │   └── mock_media/
    │
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   ├── regression/
    │   └── scenarios/
    │
    ├── docs/
    │   ├── architecture/
    │   ├── controls/
    │   ├── screenshots/
    │   └── demo/
    │
    ├── docker/
    │
    ├── compose.yaml
    ├── Makefile
    ├── README.md
    ├── SECURITY.md
    └── LICENSE
```

---

# 14. Build Blueprint

Default blueprint hierarchy:

**Node → Phase → Milestone**

- **Node:** smallest individually buildable and testable unit
- **Phase:** group of nodes forming one functional chunk
- **Milestone:** group of phases proving a major system outcome

---

# Milestone 1 — Does It Work?

## Goal

Prove that ScratchLab can:

1. Generate synthetic banking data.
2. Inject a known behavior.
3. Evaluate that behavior with an AML control.
4. Compare expected versus actual.
5. Produce PASS or FAIL.

No public enrichment. No elaborate graph. No extra infrastructure.

Get the core engine working first.

---

## Phase 1.1 — Synthetic Bank

### Node 1.1.1 — Database Foundation

Build:

```text
customers
accounts
transactions
scenarios
controls
alerts
test_runs
```

**Test:** Database initializes completely from scratch.

### Node 1.1.2 — Synthetic Customer Generator

Generate deterministic fake:

- People
- Companies
- Accounts
- Customer profiles

**Test:** The same seed produces the same customer set.

### Node 1.1.3 — Transaction Generator

Generate normal baseline banking activity.

**Test:** Generate 30, 60, or 90 days of synthetic transactions.

---

## Phase 1.2 — Scenario Engine

### Node 1.2.1 — Scenario Schema

Create structured scenario definitions.

### Node 1.2.2 — Normal Scenario

Inject legitimate baseline activity.

Expected:

```text
NO ALERT
```

### Node 1.2.3 — Rapid-Movement Scenario

Inject deliberately suspicious synthetic behavior.

Expected:

```text
ALERT
```

---

## Phase 1.3 — First Control

### Node 1.3.1 — Control Schema

Load AML control configuration from YAML.

### Node 1.3.2 — Evaluation Engine

Feed synthetic transactions into the control.

### Node 1.3.3 — Alert Generation

Create a standardized alert object when the control fires.

---

## Phase 1.4 — Test Harness

### Node 1.4.1 — Expected Result

Scenario declares:

```yaml
expected:
  alert: true
```

### Node 1.4.2 — Actual Result

Capture the monitoring engine result.

### Node 1.4.3 — Assertion Engine

Compare:

```text
EXPECTED == ACTUAL
```

Emit:

```text
PASS
```

or:

```text
FAIL
```

---

## Milestone 1 Proof

Run:

```bash
docker compose up --build
```

Open the UI.

Click:

**Inject Rapid Movement**

The system:

1. Generates fake transactions.
2. Evaluates the AML control.
3. Fires an alert.
4. Compares expected versus actual.
5. Displays:

```text
✓ PASS
```

**Milestone 1 complete.**

---

# Milestone 2 — Make It a Testing Platform

## Phase 2.1 — Scenario Library

### Nodes

Add scenarios for:

- Abnormal velocity
- Volume deviation
- Funnel activity
- Circular flow
- Dormant activation
- Customer-profile mismatch
- Legitimate high-volume activity

Each scenario requires positive and negative test coverage.

---

## Phase 2.2 — Control Management

### Node 2.2.1 — Control Loader

```text
YAML → Validated Control
```

### Node 2.2.2 — Control Versioning

Track control changes.

### Node 2.2.3 — Control Toggle

Enable and disable controls.

### Node 2.2.4 — Control Metadata

Track:

- Owner
- Description
- Severity
- Scenario coverage
- Version

---

## Phase 2.3 — Regression Runner

### Node 2.3.1 — Run-All Engine

Create:

```text
RUN ALL TESTS
```

### Node 2.3.2 — Regression Summary

Example:

```text
37 scenarios

PASS       34
FAIL        2
UNTESTED    1

Coverage 91.8%
```

### Node 2.3.3 — Intentional Regression

Change a known control and verify the suite detects the defect.

---

## Milestone 2 Proof

1. Run the entire scenario suite.
2. Intentionally modify one control.
3. Rerun the suite.
4. ScratchLab detects the regression.
5. The UI shows exactly which scenario failed and why.

---

# Milestone 3 — Build the Scratcher

## Phase 3.1 — Enrichment Framework

### Nodes

- Source adapter interface
- Enrichment job engine
- Result normalization
- Source timestamping
- Error handling
- Evidence attachment

---

## Phase 3.2 — OFAC Adapter

### Node 3.2.1 — Dataset Loader

Load public sanctions data.

### Node 3.2.2 — Entity Normalizer

Normalize:

- Names
- Aliases
- Punctuation
- Case
- Spacing

### Node 3.2.3 — Exact Match

Support deterministic exact matching.

### Node 3.2.4 — Fuzzy Match

Support candidate similarity scoring.

### Node 3.2.5 — Review Result

Output:

```text
POTENTIAL MATCH
Human review required
```

Never make a criminal determination.

---

## Phase 3.3 — FinCEN Intelligence

### Nodes

- Advisory metadata collector
- Local advisory library
- Indicator tagging
- Advisory-to-scenario mapping
- Control-coverage mapping

---

## Phase 3.4 — Mock Adverse Media

Create deterministic fake sources such as:

```text
Daily Synthetic News
Synthetic Financial Journal
Demo State Court Records
```

This keeps demos predictable and avoids associating innocent real people with criminal conduct.

---

## Milestone 3 Proof

1. Scenario creates alert.
2. Alert automatically launches enrichment.
3. ScratchLab collects relevant evidence.
4. Investigator receives one normalized evidence packet.

---

# Milestone 4 — Investigator UI

## Phase 4.1 — Command Center

### Nodes

- Control health
- Alert count
- Test coverage
- Recent failures
- Source health
- Transaction activity

---

## Phase 4.2 — Scenario Forge

### Nodes

- Scenario picker
- Parameter editor
- Seed selector
- Inject button
- Execution animation
- Expected/actual result display

---

## Phase 4.3 — Investigation Workspace

### Nodes

- Case overview
- Transaction timeline
- Customer profile
- Related accounts
- Enrichment panel
- Analyst notes
- Evidence viewer

---

## Phase 4.4 — Entity Graph

### Nodes

- Graph API
- Customer nodes
- Account nodes
- Transaction relationships
- Entity relationships
- Sanctions candidate nodes
- Expandable evidence drawer

---

## Milestone 4 Proof

A new user can open ScratchLab without explanation and understand:

```text
What happened
      ↓
Why it alerted
      ↓
What evidence exists
      ↓
Whether the control passed
```

---

# Milestone 5 — Compliance Test Lab

## Phase 5.1 — Control Matrix

Build scenario × control coverage.

---

## Phase 5.2 — Evidence Vault

Store complete reproducible test packages.

---

## Phase 5.3 — Defect Management

Failures become findings.

Example:

```text
Finding AML-F-008

Control:
AML-CIR-001

Expected:
HIGH alert

Actual:
No alert

Cause:
ACH transaction class excluded

Severity:
HIGH

Status:
OPEN
```

---

## Phase 5.4 — Before / After Testing

Fix the control.

Run the same dataset seed again.

```text
BEFORE    FAIL
AFTER     PASS
```

---

## Milestone 5 Proof

ScratchLab:

1. Detects an intentional AML monitoring defect.
2. Records the evidence.
3. Tracks the finding.
4. Repeats the same scenario after remediation.
5. Proves the fix with regression testing.

---

# Milestone 6 — Portfolio Release

## Phase 6.1 — Demo Bank

Ship a deterministic synthetic environment:

```text
Scratch National Bank
```

Initial target:

```text
250 customers
400 accounts
~25,000 transactions
15 AML scenarios
10 monitoring controls
5 intentional defects
```

Final values can change after performance testing.

---

## Phase 6.2 — GitHub Polish

README structure:

```text
SCRATCHLAB
Synthetic AML Compliance Testing Platform

[Dashboard GIF]

✓ Synthetic Banking
✓ AML Controls-as-Code
✓ Scenario Injection
✓ Regression Testing
✓ OFAC Enrichment
✓ Entity Analysis
✓ Evidence Collection
✓ Control Coverage
```

Include:

- Architecture
- Screenshots
- Demo GIF
- Local setup
- Test instructions
- Synthetic-data disclaimer
- Security notes

---

## Phase 6.3 — One-Command Demo

Run:

```bash
git clone <repo>
cd aml-scratch-lab
docker compose up --build
```

Open:

```text
http://localhost:3000
```

API docs:

```text
http://localhost:8000/docs
```

---

## Milestone 6 Final Proof

A recruiter clones:

```text
milkmastermike/aml-scratch-lab
```

Runs one Docker command.

Opens the browser.

Clicks:

# RUN DEMO

And watches:

```text
Generate Bank
     ↓
Inject Scenario
     ↓
Process Transactions
     ↓
Trigger Control
     ↓
Create Alert
     ↓
Scratch Evidence
     ↓
Build Entity Graph
     ↓
Test Expected vs Actual
     ↓

        ✓ PASS

or

        ✕ CONTROL FAILURE
```

No fake screenshots.

No prerecorded result.

The system actually performs the test.

---

# V1 Boundaries

Do **not** add these to V1:

- AI chatbot
- LLM deciding whether someone is suspicious
- Actual SAR submission
- Real customer information
- Proprietary bank rules
- Kubernetes
- Complex cloud infrastructure
- Production banking claims

Keep the portfolio story clean.

---

# Portfolio Description

> **ScratchLab is a local, containerized AML compliance-testing environment that creates reproducible synthetic banking scenarios, validates transaction-monitoring controls, enriches alerts from public intelligence sources, visualizes entity relationships, and preserves evidence of expected-versus-actual control behavior.**

The project demonstrates:

- Software development
- QA automation
- Compliance testing
- AML concepts
- APIs
- SQL
- Docker
- Data analysis
- Cybersecurity discipline
- Frontend development
- Evidence handling
- Regression testing
