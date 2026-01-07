PROJECT_HANDBOOK.md
===================

Monarch+ Dashboard — Project Handbook (Source of Truth)

Last Updated: Current
Status: Active

------------------------------------------------------------
1) Purpose & Outcomes
------------------------------------------------------------

Build a Streamlit-based personal finance dashboard (“Monarch+”) that ingests CSV exports (starting with Monarch Money) and delivers analytics beyond Monarch’s native UI.

The dashboard must be:
- Stable first, aesthetic second
- Suitable for personal use and future financial coaching clients
- Extensible without breaking ingestion, metrics, or filters

Primary design principle:
Correctness, stability, and architectural clarity always outweigh visual polish.

------------------------------------------------------------
2) Core UX & Layout Rules (Non-Negotiable)
------------------------------------------------------------

Navigation
- Top-level navigation MUST use horizontal tabs
- No sidebar-based tab navigation

Persistent Left Control Panel
- A single persistent left-hand control panel must exist across ALL tabs
- This panel is structural infrastructure, not tab content
- The panel must NOT re-render per tab

The left control panel contains:
- CSV upload (Transactions + Accounts)
- Period selection (Q1–Q4, ALL YEARS)
- Date range display (label on top, dates underneath)
- Include / Exclude toggles (Transfers, Credit Card Payments, etc.)
- Status indicators
- Reset Dashboard button

Layout Structure
- Left: persistent control panel
- Center/Right: tab-specific content
- No duplicated controls inside tabs
- No logic tied to tab rendering order

------------------------------------------------------------
3) Date & Period Rules
------------------------------------------------------------

Period Selection
- Supported periods:
  - Q1, Q2, Q3, Q4
  - ALL YEARS
- Period controls must be horizontal and visually compact
- ALL YEARS must be symmetrical with Q1–Q4 (either first or last)

Date Range Display
- Must show:
  - “Date Range” label
  - Actual start/end dates on the line below
- Display format must be consistent across all tabs

Filtering Discipline
- Period + date filtering happens ONCE
- All tabs consume the same filtered dataset
- Tabs must NEVER apply independent filters

------------------------------------------------------------
4) Data Ingestion & State Management (Critical)
------------------------------------------------------------

Single Ingestion Rule
- CSV ingestion happens ONLY on:
  - File upload
  - Reset Dashboard
- Switching tabs must NEVER trigger ingestion

Session State
- Normalized data must live in st.session_state:
  - transactions_df
  - accounts_df
- All tabs, charts, and tables read from session state ONLY

Reset Dashboard Behavior
- Reset must:
  - Clear all CSV-derived session_state
  - Clear the Streamlit file uploader queue
  - Restore default filters
- Reset must NOT cause reload loops or crashes

Error Handling
- No silent failures
- Missing or ambiguous columns must show readable user-facing errors
- Pandas DataFrames must NEVER be used in boolean contexts

------------------------------------------------------------
5) Transaction Filtering Rules (Canonical Pipeline)
------------------------------------------------------------

Single Source of Truth
- ALL transaction filtering occurs in ONE canonical pipeline
- Filters include:
  - Date range
  - Period
  - Include / Exclude Transfers
  - Include / Exclude Credit Card Payments
  - Keyword include/exclude rules (future-safe)

Transfer Handling
- Transfers must be detected using a robust helper:
  - Transaction type
  - Category name
  - Known transfer patterns
- Toggling “Include transfers” MUST change:
  - Transaction count
  - Income totals
  - Expense totals
  - Net cash flow
  - Charts
  - Tables

No duplicated filtering logic is allowed anywhere else.

------------------------------------------------------------
6) Dashboard Content Rules
------------------------------------------------------------

Key Metrics
- Displayed in a single horizontal grid
- Grouping:
  - Income, Expenses, Net Cash Flow
  - Assets, Liabilities, Net Worth

Formatting
- Accounting format for negatives: ($1,234.56)
- Always include commas and currency symbols
- Hover tooltips must show formatted values

Charts
- Chart type changes must be isolated and safe to modify later
- Cash Flow:
  - Income and Expenses shown side-by-side (not stacked)
- Balance Snapshot:
  - Pie chart for Assets / Liabilities / Net Worth
  - Labels and values must be visible without hover

Data Grids
- Every chart must have a corresponding data grid underneath
- Grids must be collapsible using st.expander
- All expanders MUST use deterministic, unique keys
- Grids reuse the Transactions tab table style

------------------------------------------------------------
7) Transactions Tab Rules
------------------------------------------------------------

- Displays the fully filtered dataset
- Sorting, searching, and filtering reflect the same canonical state
- No separate or duplicated logic paths

------------------------------------------------------------
8) Architecture & Code Organization
------------------------------------------------------------

Separation of Concerns
- UI modules render only
- Logic modules compute only
- No business logic inside Streamlit layout code

Recommended Structure
- src/ingest.py          → CSV normalization
- src/filters.py         → Canonical filtering pipeline
- src/metrics.py         → Financial calculations
- src/date_filters.py    → Period + date logic
- ui/control_panel.py    → Persistent left panel
- ui/dashboard.py        → Dashboard tab
- ui/transactions.py    → Transactions tab
- ui/insights.py         → Insights tab

Refactor early. Avoid monolithic files.

------------------------------------------------------------
9) Definition of Done (PR Acceptance Criteria)
------------------------------------------------------------

A PR is DONE only when ALL conditions below are met:

- App loads with no CSVs uploaded
- Uploading CSVs never crashes the app
- Switching tabs does not reset state
- Filters materially change numbers when applicable
- Reset Dashboard clears data and uploader queue cleanly
- No Streamlit runtime errors:
  - DuplicateWidgetID
  - st.expander key collisions
  - pandas truth-value ambiguity
- Charts and tables agree numerically
- PR scope matches stated objective

------------------------------------------------------------
10) GitHub PR Template (Required)
------------------------------------------------------------

PR Title:
[Short, descriptive, specific]

Objective:
What this PR changes and why.

Changes Included:
- Bullet list of concrete changes

Acceptance Criteria:
- [ ] App loads with no CSVs
- [ ] Filters affect metrics
- [ ] No Streamlit runtime errors
- [ ] Reset works correctly

How to Validate:
1. Upload CSVs
2. Toggle filters
3. Switch tabs
4. Reset dashboard
5. Confirm stability

Out of Scope:
Explicitly list what is NOT addressed.

------------------------------------------------------------
11) Workflow (Chat + GitHub Only)
------------------------------------------------------------

Current workflow:
1. Define PR scope in chat
2. Implement changes manually in a feature branch
3. Open GitHub PR into main
4. Review against Definition of Done
5. Merge only when stable in Streamlit Cloud

Codex is currently NOT used.

------------------------------------------------------------
12) Copy-Ready Response Rule (Strict)
------------------------------------------------------------

ALL instructions, PR definitions, templates, and scripts MUST:
- Be delivered inside a single fenced code block
- Be fully copyable using the UI copy button
- Require ZERO manual typing

If something must be typed manually, the instructions are incomplete.

------------------------------------------------------------
END OF HANDBOOK
------------------------------------------------------------
