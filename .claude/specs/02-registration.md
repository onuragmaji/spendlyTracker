# Spec: Registration

## Overview
Make the registration form functional by adding a `POST /register` route that
validates input, creates a new user record in SQLite, and redirects to the
login page on success. This step introduces Flask sessions (needed by all
subsequent authenticated routes) and the `create_user` / `get_user_by_email`
DB helpers that the login step will reuse.

## Depends on
- Step 01 — Database Setup (`get_db()`, `users` table, `werkzeug` available)

## Routes
- `POST /register` — validates form data, creates user, redirects — public

## Database changes
No new tables or columns. The `users` table from Step 01 already has the
required schema. Two new helper functions are added to `database/db.py`:

- `create_user(name, email, password_hash)` — inserts a row, returns the new
  `user_id`, raises `sqlite3.IntegrityError` on duplicate email.
- `get_user_by_email(email)` — returns the matching `sqlite3.Row` or `None`.
  (Used by the login step; included here so the DB layer is complete.)

## Templates
- **Modify:** `templates/register.html`
  - Change `action="/register"` to `action="{{ url_for('register') }}"` to
    remove the hardcoded URL.
  - Re-populate `name` and `email` fields with `value="{{ request.form.get('name', '') }}"` 
    etc. so values survive a validation error round-trip.

## Files to change
- `app.py` — add `app.secret_key`, import `session`, `redirect`, `url_for`,
  `request`, `flash`; convert `GET /register` stub into a combined
  `GET + POST` route.
- `database/db.py` — add `create_user()` and `get_user_by_email()`.
- `templates/register.html` — fix hardcoded action URL; add field value
  persistence on error.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already
imported in `database/db.py`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — never f-strings in SQL.
- Hash passwords with `werkzeug.security.generate_password_hash`.
- Catch `sqlite3.IntegrityError` to detect duplicate email — do not pre-check
  with a `SELECT` and then `INSERT` (TOCTOU race).
- `app.secret_key` must be set before any `session` usage; use a hardcoded
  dev string for now (e.g. `"dev-secret-change-in-prod"`).
- All templates must extend `base.html`.
- Use CSS variables — never hardcode hex values.
- Use `url_for()` for every internal link and form action.
- Validation rules:
  - Name: required, stripped, non-empty.
  - Email: required (rely on `<input type="email">` + server non-empty check).
  - Password: required, minimum 8 characters.
- On validation failure: re-render `register.html` with `error=<message>` and
  preserved field values.
- On success: redirect to `url_for('login')` (profile is a stub until Step 4).
- Use `abort(405)` for unexpected methods, not bare string returns.

## Definition of done
- [ ] `POST /register` with valid data creates a user row in `users`.
- [ ] Passwords are stored as hashes — never plaintext.
- [ ] Duplicate email shows an error on the register page, does not crash.
- [ ] Password shorter than 8 characters shows a validation error.
- [ ] Empty name or email shows a validation error.
- [ ] After successful registration, browser is redirected to `/login`.
- [ ] Name and email fields are repopulated after a failed submission.
- [ ] `GET /register` still renders the empty form without error.
- [ ] `get_user_by_email()` returns a row for an existing email, `None` otherwise.
- [ ] App starts without errors; no existing tests are broken.
