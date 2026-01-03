## PR Summary
**PR Number:** PR-XXX  
**Objective:**  
<!-- One sentence: what this PR changes -->

---

## Acceptance Criteria
- [ ] AC1:
- [ ] AC2:
- [ ] AC3:

---

## Implementation Notes
<!-- Brief bullets: what you changed and why -->
- 
- 

---

## Files Changed
<!-- List files modified/added -->
- 
- 

---

## Validation Steps
<!-- What to click/run inside the Streamlit app to verify -->
- [ ] Upload Monarch CSV(s)
- [ ] Confirm primary tabs render (Dashboard / Transactions / Insights)
- [ ] Confirm year tabs render under each primary tab (ALL + per-year)
- [ ] Confirm quarter presets (Q1–Q4) behave within selected year
- [ ] Confirm formatting: liabilities use parenthetical accounting format

---

## Monarch+ PR Review Checklist (Must Pass)

### UX & Layout (Non-Negotiables)
- [ ] Top-level navigation uses horizontal tabs (no sidebar)
- [ ] Secondary year tabs exist under each primary tab (ALL + per-year)
- [ ] Year tabs reuse identical modules/layout (no duplicated logic)
- [ ] Quarter presets only (Q1–Q4); no WTD/MTD reintroduced
- [ ] “Date Range” label and displayed dates are consistent across tabs
- [ ] Dashboard layout follows modular, vertical flow (trading dashboard rhythm)

### Data & Ingestion
- [ ] CSV column mapping is resilient to Monarch variations
- [ ] Missing/ambiguous required fields show a clear user-facing error
- [ ] Dates parsed consistently; numeric coercion is safe (no silent NaNs)

### Formatting
- [ ] Liabilities/negative values use accounting format: ($25,000), not $-25,000

### Architecture
- [ ] Streamlit UI stays thin; business logic lives in `src/`
- [ ] Code placed in correct module(s) (ingest/metrics/categories/recurring/date_filters)
- [ ] No monolithic scripts introduced; refactor if file grows too large

### Stability
- [ ] App cold-starts without errors
- [ ] No regressions to existing tabs/features

---

## Notes / Follow-Ups (Optional)
<!-- Any known limitations, next steps, or deferred items -->
- 
