# Spec: Add Expense

## Overview
This feature replaces the stub `GET /expenses/add` route with a fully functional expense-creation flow. A logged-in user fills out a form (amount, category, date, optional description) and submits it; the server validates the input, inserts a row into the `expenses` table, and redirects to the profile page with a success flash message. This is the first write path for expense data and is a prerequisite for the edit and delete steps that follow.

## Depends on
- Step 01 — Database setup (expenses table schema)
- Step 03 — Login and logout (session-based auth)
- Step 05 — Backend routes for profile (profile page to redirect to after save)

## Routes
- `GET /expenses/add` — render the empty add-expense form — logged-in only
- `POST /expenses/add` — validate and insert expense, then redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The existing `expenses` table has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

A new DB helper `add_expense(user_id, amount, category, date, description)` must be added to `database/db.py`.

## Templates
- **Create:** `templates/expenses/add.html` — form page extending `base.html`
- **Modify:** none

## Files to change
- `app.py` — replace the GET-only stub at lines 141–143 with a full GET/POST handler
- `database/db.py` — add `add_expense()` helper

## Files to create
- `templates/expenses/add.html` — expense form template
- `static/css/add-expense.css` — page-specific styles (imported via block in add.html)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterized queries only — never f-strings or `.format()` in SQL
- Passwords hashed with werkzeug (not relevant here, but carry-forward rule)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard: redirect to `/login` if `session.get("user_id")` is missing
- Categories are fixed — use a Python list constant in `app.py`, not a DB query: `["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]`
- `amount` must be a positive float; reject zero or negative values
- `date` must be a valid ISO date (reuse `_valid_date()` from `app.py`); default to today if blank
- `description` is optional; store `None` if blank
- On validation failure, re-render the form with an error message and preserve the user's input
- On success, flash a confirmation message and redirect to `/profile` with `302`
- `add_expense()` in `database/db.py` must be the only place SQL is written for this insert

## Definition of done
- [ ] `GET /expenses/add` renders the form for a logged-in user
- [ ] `GET /expenses/add` redirects to `/login` for an unauthenticated user
- [ ] Submitting the form with valid data inserts one row into `expenses` and redirects to `/profile`
- [ ] The new expense appears in the transactions list on `/profile` immediately after redirect
- [ ] Submitting with a non-numeric amount shows an inline error and does not insert a row
- [ ] Submitting with amount ≤ 0 shows an inline error and does not insert a row
- [ ] Submitting with an invalid date shows an inline error and does not insert a row
- [ ] Category dropdown contains exactly the 7 fixed categories
- [ ] Leaving description blank succeeds (stored as NULL)
- [ ] The form page is styled consistently with the rest of the app using CSS variables
