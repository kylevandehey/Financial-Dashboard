# AGENTS.md — Monarch+ Dashboard  
## Purpose of This Document

This file is the authoritative operating handbook for Codex when working on the Monarch+ Dashboard.

Codex must follow these rules exactly. Deviation from these rules is considered a failed task, regardless of whether code “works.”

---

## Project Overview

Monarch+ is a Streamlit-based personal finance dashboard that ingests CSV exports (starting with Monarch Money) and delivers analytics beyond Monarch’s native UI.

The dashboard must support:
- Personal use
- Future financial coaching clients
- Long-term extensibility without UX refactors

---

## Non-Negotiable UX Rules

### Navigation
- Navigation must use **top-level horizontal tabs**
- Sidebar navigation is **not allowed**

### Primary Tabs (Examples)
- Dashboard
- Transactions
- Insights
- Loans (future)
- Assistant (future)

---

## Year-Based Segmentation (Critical UX Requirement)

Within each primary tab, the layout must include **secondary, horizontal year-based tabs** that replicate the trading dashboard pattern.

### Required Structure
Each primary tab must include:
- **ALL** (aggregated view across all years)
- Individual year tabs derived dynamically from data:
  - 2025
  - 2024
  - 2023
  - etc.

### Behavior Rules
- The **ALL** tab shows combined data across all available years
- Year tabs filter the **exact same layout and modules** to that year only
- No duplicated logic between ALL and year tabs
- Year tabs must appear visually **below the main navigation tabs**
- This structure must be consistent across all primary tabs

This pattern must mirror the tabular module flow and year segmentation used in the referenced trading dashboard screenshots.

---

## Date Filtering Rules

- Year tabs are the **primary time segmentation mechanism**
- Date filtering must operate **within the selected year context**
- Supported preset ranges are:
  - Q1
  - Q2
  - Q3
  - Q4
- Custom date ranges must be supported
- Deprecated concepts (e.g., Week-to-Date, Month-to-Date) must **not** be reintroduced

---

## Financial Formatting Rules

- Negative values for liabilities must use **accounting format**
  - Correct: `($25,000)`
  - Incorrect: `$-25,000`
- This applies everywhere:
  - Metric cards
  - Tables
  - Summaries
  - Exports

---

## Metric Cards

Category summary metric boxes must:
- Include income and expense categories
- Show **Top 5** by default
- Include **“Show More”** to expand
- Default to `st.metric()`-style cards
- Optionally support table/grid view

Visual style must match the trading dashboard:
- Icon usage
- Bold emphasis
- Clear hierarchy

---

## Layout Rules

- Dashboard content must follow a **modular, vertical flow**
- Modules should feel like stacked dashboard blocks
- Visual density and rhythm must match the trading dashboard screenshots
- No ad-hoc or tab-specific layout inventions

---

## Functional Scope

### Core (Now)
- CSV upload and summary:
  - Total transactions
  - Date range
  - Total income
  - Total expenses
  - Assets, liabilities, equity (where supported)
- Transactions tab:
  - Searchable
  - Filterable
- Insights tab:
  - Recurring expense detection
  - Rolling trends
  - Savings rate
  - Burn rate
  - Category-level volatility
  - Versioned financial health score

### Expandable (Later)
- Loan tracker with amortization and payoff strategies
- Tax readiness export
- Cash flow projections and sinking funds
- Automated client PDF reports
- Embedded assistant module
- Login/auth module (placeholder visible, not enforced)

---

## Data and Ingestion Rules

Ingestion must be resilient:
- Map columns when Monarch exports differ
- Parse dates consistently
- Coerce numeric types safely
- Validate required fields

No silent failures:
- Missing or ambiguous columns must produce clear, readable error messages
- Errors must explain how to fix the issue

---

## Architecture and Code Organization

### Separation of Concerns
- Streamlit UI must remain thin
- Business logic must live in isolated, testable Python modules

### Recommended Structure
- `src/ingest.py` — CSV normalization
- `src/metrics.py` — core calculations
- `src/categories.py` — category rollups
- `src/recurring.py` — recurring detection
- `src/date_filters.py` — year + quarter logic
- `ui/` — tab render functions only

Avoid monolithic scripts. Refactor proactively when files grow.

---

## Testing and Quality Gates

- Add lightweight unit tests for:
  - Ingestion mapping
  - Metrics
  - Recurring detection
- Provide at least one fast smoke test:
  - Validates imports
  - Validates compilation
- Each PR should:
  - Be small
  - Address one feature or fix only

---

## Codex Workflow Rules (Mandatory)

- Codex must implement work via PRs
- Each task prompt must include:
  - Objective
  - Acceptance criteria
  - Files/modules impacted
  - Validation steps
  - Constraints (UX and logic)
- Codex must restate constraints explicitly in the PR description

---

## Review Authority

Kyle is the sole reviewer.

Merge only when:
- All acceptance criteria are met
- All checklist items in the GitHub PR template are satisfied

“Mostly correct” is not acceptable.

---

## Definition of Done (Monarch+)

A pull request is considered complete when:

1. The PR objective matches its acceptance criteria exactly
2. The GitHub PR checklist is fully satisfied
3. Year-based segmentation behaves correctly (ALL + per-year tabs)
4. UX and formatting rules are preserved
5. No regressions are introduced
6. Architecture rules are followed
7. No automated Codex code review is required

Codex may be used for implementation and PR generation, but final validation is human-driven.

---

## Change Tracking

Maintain a `CHANGELOG.md` or PR log summarizing major changes as the app evolves.

Optional but strongly recommended.


