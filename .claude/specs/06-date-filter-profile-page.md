# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so users can scope all three
data sections — summary stats, transaction list, and category breakdown — to a
specific time window. Users can choose a preset range ("This Month",
"Last 3 Months") or enter a custom from/to date. The filter is applied via
`from_date` and `to_date` query parameters on `GET /profile`; omitting both
parameters preserves the existing all-time view. This is the first
user-configurable view of expense data and is a prerequisite for more advanced
reporting in later steps.

## Depends on
- Step 1: Database setup (`expenses.date` column, TEXT ISO format `YYYY-MM-DD`)
- Step 3: Login / Logout (`session["user_id"]` set on login)
- Step 4: Profile page design (template structure already in place)
- Step 5: Backend routes for profile (live query helpers in `database/queries.py`)

## Routes
No new routes. `GET /profile` is extended to accept optional query parameters:
- `from_date` — ISO date string `YYYY-MM-DD`, inclusive lower bound (optional)
- `to_date` — ISO date string `YYYY-MM-DD`, inclusive upper bound (optional)

## Database changes
No database changes. The `expenses.date` column (`TEXT NOT NULL`, ISO format)
already supports range queries with `>=` / `<=` comparisons.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date filter form above the stats tiles (method GET, action `url_for('profile')`)
  - Include two `<input type="date">` fields: `from_date` and `to_date`
  - Include three preset buttons that pre-fill the date inputs via vanilla JS:
    - "This Month" — first day of current month → today
    - "Last 3 Months" — 3 calendar months ago → today
    - "All Time" — clears both fields (submits with no date params)
  - Include an "Apply" submit button
  - Preserve the selected `from_date` / `to_date` values in the inputs after
    form submission (pass them from the route via template context)
  - Show an active-filter label above the tiles when a filter is in effect,
    e.g. "Showing: 1 Apr 2026 – 30 Apr 2026"

## Files to change
- `app.py` — read `from_date` and `to_date` from `request.args` in `profile()`;
  pass both to each query helper; pass them back to the template as context
- `database/queries.py` — add optional `from_date=None` / `to_date=None`
  parameters to `get_summary_stats`, `get_recent_transactions`, and
  `get_category_breakdown`; extend each SQL query with `AND date >= ?` /
  `AND date <= ?` clauses when the parameters are provided
- `templates/profile.html` — date filter form and active-filter label (see above)
- `static/css/profile.css` — styles for the filter bar (inputs, preset buttons,
  apply button, active-filter label); use CSS variables only

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Date inputs must use `type="date"` HTML5 inputs — no third-party pickers
- When `from_date` and `to_date` are both absent, query helpers must behave
  identically to Step 5 (all-time data, no regression)
- Filter must be applied consistently across all three sections — stats,
  transaction list, and category breakdown must all reflect the same range
- The 10-row limit in `get_recent_transactions` still applies within the
  filtered range (show at most 10 most-recent transactions in range)
- Preset buttons pre-fill the date inputs using vanilla JS only — no libraries
- `from_date` / `to_date` values must be validated in the route: if either is
  provided but not a valid `YYYY-MM-DD` string, silently treat it as absent
  (do not abort or raise)
- Passwords hashed with werkzeug (no change — existing auth is unaffected)

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data — no regression
      from Step 5 behavior
- [ ] A date filter form appears above the summary tiles with two date inputs and
      three preset buttons
- [ ] Clicking "This Month" and submitting filters all three sections to the
      current calendar month only
- [ ] Clicking "Last 3 Months" and submitting shows only data from the past 3
      calendar months
- [ ] Clicking "All Time" clears the inputs and submitting restores the all-time view
- [ ] Entering a custom `from_date` and `to_date` and clicking "Apply" filters all
      three sections to that range
- [ ] After submitting, the `from_date` and `to_date` inputs are pre-filled with
      the active filter values
- [ ] When a date filter is active, an active-filter label is visible showing the
      effective date range
- [ ] A user with no expenses in the selected range sees ₹0.00 total spent,
      0 transactions, and an empty category breakdown with no errors
