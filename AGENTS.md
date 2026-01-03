AGENTS.md — Monarch+ Dashboard
Purpose of This Document

This file is the authoritative operating handbook for Codex when working on the Monarch+ Dashboard.

Codex must follow these rules exactly.
Deviation from these rules is considered a failed task, regardless of whether code “works.”

1) Project Overview

Monarch+ is a Streamlit-based personal finance dashboard that ingests CSV exports (starting with Monarch Money) and delivers analytics beyond Monarch’s native UI.

The dashboard must support:

Personal use

Future financial coaching clients

Long-term extensibility without UX refactors

2) Non-Negotiable UX Rules
Navigation

Navigation must use top-level horizontal tabs

Sidebar navigation is not allowed

Primary Tabs (Examples)

Dashboard

Transactions

Insights

Loans (future)

Assistant (future)

Yearly Breakout Tabs (Critical UX Requirement)

Within each primary tab, the layout must include secondary, horizontal year-based tabs that replicate the trading dashboard pattern.

Required Structure

Each primary tab must include:

ALL (aggregated view)

Individual year tabs, e.g.:

2025

2024

2023

etc. (derived dynamically from data)

Behavior Rules

ALL tab shows combined data across all available years

Year tabs filter the exact same layout and modules to that year only

No duplicated logic between ALL and year tabs

Year tabs must appear visually below the main navigation tabs

This structure must be consistent across all primary tabs

This pattern must mirror the tabular module flow and year segmentation used in the referenced trading dashboard screenshots.

Date Filtering

Default view is YTD

Provide:

Preset dropdowns

One-click buttons

Must support:

Last Week-to-Date

Month-to-Date (MTD)

Year-to-Date (YTD)

Q1

Q2

Q3

Q4

Support custom date ranges

Date filtering must respect:

ALL vs Year tabs

Selected year context

Financial Formatting

Negative values for liabilities must use accounting format

Correct: ($25,000)

Incorrect: $-25,000

This applies everywhere: metrics, tables, summaries, exports

Metric Cards

Category summary metric boxes must:

Include income and expense categories

Show Top 5 by default

Include “Show More” to expand

Default to st.metric()-style cards

Optionally support table/grid view

Visual style must match the trading dashboard:

Icon

Bold emphasis

Clear hierarchy

Layout Rules

Dashboard content must follow a modular, vertical flow

Modules should feel like stacked dashboard blocks

Visual density and flow must match the trading dashboard screenshots

No ad-hoc layouts per tab

3) Functional Scope
Now (Core)

CSV upload and summary:

total transactions

date range

total income

total expenses

assets, liabilities, equity (where supported)

Transactions tab:

searchable

filterable

Insights tab:

recurring expense detection

rolling trends

savings rate

burn rate

category-level volatility

versioned financial health score

Later (Expandable)

Loan tracker with amortization and payoff strategies

Tax readiness export

Cash flow projections and sinking funds

Automated client PDF reports

Embedded assistant module

Login/auth module

Placeholder visible

Not enforced until final stage

4) Data and Ingestion Rules

Ingestion must be resilient:

Map columns when Monarch exports differ

Parse dates consistently

Coerce numeric types safely

Validate required fields

No silent failures:

Missing or ambiguous columns must produce clear, readable error messages

Errors must explain how to fix the issue

5) Architecture and Code Organization
Separation of Concerns

Streamlit UI must be thin

Business logic must live in isolated, testable Python modules

Recommended Structure

src/ingest.py — CSV normalization

src/metrics.py — core calculations

src/categories.py — category rollups

src/recurring.py — recurring detection

src/date_filters.py — presets + YTD + year logic

ui/ — tab render functions only

Avoid monolithic scripts

Refactor proactively when files grow

6) Testing and Quality Gates

Add lightweight unit tests for:

ingestion mapping

metrics

recurring detection

Provide at least one fast “smoke test”:

validates imports

validates compilation

Each PR should:

be small

address one feature or fix only

7) Codex Workflow Rules (Mandatory)

Codex must implement work via PRs

Each task prompt must include:

objective

acceptance criteria

files/modules impacted

validation steps (commands)

constraints (UX and logic)

Codex must explicitly restate constraints in its PR description

8) Review Authority

Kyle is the sole reviewer

Merge only when all acceptance criteria are met

“Mostly correct” is not acceptable

9) Definition of Done

A task is done only when:

UX rules are followed exactly

Yearly breakout tabs behave correctly

No regressions introduced

Code structure matches architecture rules

Formatting rules are preserved

Acceptance criteria are explicitly verified

10) Change Tracking

Maintain a CHANGELOG.md or PR log

Summarize major changes as the app evolves

Optional but strongly recommended

## Definition of Done (Monarch+)

A pull request is considered complete when:

1. The PR objective matches acceptance criteria exactly
2. All applicable items in the Monarch+ PR Review Checklist are satisfied
3. UI constraints are preserved:
   - Horizontal top navigation
   - Default YTD date view
4. Business logic remains isolated from Streamlit UI
5. CSV ingestion errors are user-visible
6. No automated Codex code review is required

Codex may be used for implementation and code generation, but final review is human-driven.

