# Spec: Profile Page Design

## Overview
This step implements the `/profile` route, turning the current stub into a fully rendered
page. The profile page displays the logged-in user's account details (name, email, member-since
date) alongside a statistical summary of their expense history: total expenses recorded, total
amount spent, and a per-category breakdown. It is read-only — no editing of account data or
expenses in this step. The route is protected: unauthenticated visitors are redirected to `/login`.

## Depends on
- Step 1 — Database setup (users and expenses tables, `get_db()`)
- Step 2 — Registration (user records in the DB)
- Step 3 — Login / Logout (session stores `user_id` and `user_name`)

## Routes
- `GET /profile` — renders the profile page with user info and expense stats — logged-in only

## Database changes
Two new read-only query helpers in `database/db.py`:

- `get_user_by_id(user_id)` — fetches a single user row by primary key  
- `get_expense_stats(user_id)` — returns a dict with:
  - `total_count` — total number of expense rows for this user
  - `total_amount` — sum of all expense amounts (0.00 if none)
  - `by_category` — list of `(category, count, subtotal)` rows, ordered by subtotal descending

No schema changes — all queries are against existing tables.

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; displays user info card and stats section
- **Modify:** none

## Files to change
- `app.py` — replace stub string return with auth guard + real render
- `database/db.py` — add `get_user_by_id()` and `get_expense_stats()`

## Files to create
- `templates/profile.html`
- `static/css/profile.css`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Passwords must never be passed to the template
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard: if `session.get('user_id')` is falsy, `redirect(url_for('login'))`
- DB logic stays in `database/db.py` — the route only calls helpers and renders
- Import the two new helpers at the top of `app.py` alongside existing imports
- The profile CSS file must be linked only from `profile.html`, not from `base.html`

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in renders the page without errors
- [ ] The page displays the user's name and email
- [ ] The page displays the member-since date formatted as a human-readable string (e.g. "May 2 2026")
- [ ] The page displays the total number of expenses and total amount spent
- [ ] The page displays a per-category breakdown table
- [ ] For the seeded demo user all 8 seeded expenses are reflected in the stats
- [ ] A user with zero expenses sees a zero total and an empty category table (no crash)
- [ ] No raw SQL appears in `app.py`
- [ ] `pytest` passes with no regressions
