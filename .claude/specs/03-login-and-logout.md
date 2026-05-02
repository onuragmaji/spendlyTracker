# Spec: Login and Logout

## Overview
Make the login form functional by adding a `POST /login` route that validates
credentials against the database, establishes a Flask session on success, and
redirects the user to their profile. Also implement `GET /logout` to clear the
session and return the user to the landing page. Together these two routes
complete the full auth cycle that all future protected routes depend on.

## Depends on
- Step 01 — Database Setup (`get_db()`, `users` table, `get_db()` with FK on)
- Step 02 — Registration (`create_user()`, `get_user_by_email()` in `database/db.py`)

## Routes
- `POST /login` — validates email + password, sets session, redirects — public
- `GET /logout` — clears session, redirects to landing — public (no-op if not logged in)

## Database changes
No new tables or columns. All required data (`id`, `email`, `password_hash`) is
already in the `users` table from Step 01.

## Templates
- **Modify:** `templates/login.html`
  - Change form `action` to `action="{{ url_for('login') }}"`.
  - Add `method="POST"` to the `<form>` tag if not already present.
  - Display `{{ error }}` when passed from the route (validation / bad credentials).
  - Re-populate the `email` field with `value="{{ request.form.get('email', '') }}"` 
    so it survives a failed submission round-trip.

## Files to change
- `app.py`
  - Convert `GET /login` stub into a combined `GET + POST` route.
  - Import `check_password_hash` from `werkzeug.security`.
  - Implement `GET /logout` — call `session.clear()`, redirect to `url_for('landing')`.
- `templates/login.html` — fix form action, add error display, persist email field.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` ships with the
`werkzeug` package already in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — `get_user_by_email()` already handles this.
- Use `werkzeug.security.check_password_hash` to verify passwords — never compare plaintext.
- Store only `user_id` and `user_name` in `session` — never store the password hash.
- Use `session.clear()` in logout — do not delete individual keys.
- All templates must extend `base.html`.
- Use CSS variables — never hardcode hex values.
- Use `url_for()` for every internal link and form action.
- Validation rules:
  - Email: required, stripped, non-empty.
  - Password: required, non-empty.
- On validation failure or wrong credentials: re-render `login.html` with a
  generic `error="Invalid email or password."` — do not distinguish which field
  was wrong (prevents user enumeration).
- On success: set `session['user_id']` and `session['user_name']`, then
  redirect to `url_for('landing')`.
- `GET /logout` must redirect unconditionally — it is not an error to log out
  when already logged out.

## Definition of done
- [ ] `POST /login` with valid credentials sets `session['user_id']` and `session['user_name']`.
- [ ] After successful login, browser is redirected to `/`.
- [ ] Wrong password shows `"Invalid email or password."` on the login page without crashing.
- [ ] Unknown email shows the same generic error — does not reveal whether the account exists.
- [ ] Empty email or empty password shows a validation error before any DB query.
- [ ] Email field is re-populated after a failed login attempt.
- [ ] `GET /login` still renders the empty form (no error, no prefill).
- [ ] `GET /logout` clears the session and redirects to `/`.
- [ ] Logging out when not logged in redirects to `/` without error.
- [ ] App starts without errors; no existing tests are broken.
