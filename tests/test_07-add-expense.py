"""
tests/test_07-add-expense.py

Tests for Step 7: Add Expense
Covers the GET and POST /expenses/add routes.

Spec reference: .claude/specs/07-add-expense.md
"""

import pytest
from datetime import date

import app as flask_app
import database.db as db_module


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _login_as(client, user_id):
    """Inject user_id directly into the Flask test session — no password round-trip."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _count_expenses(user_id):
    """Return the number of expense rows in the DB for the given user."""
    conn = db_module.get_db()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        )
        return cur.fetchone()[0]
    finally:
        conn.close()


def _get_latest_expense(user_id):
    """Return the most recently inserted expense row for a user, or None."""
    conn = db_module.get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# conftest.py provides: app, client, seed_user, empty_user.
# The fixture below provides a logged-in client tied to a fresh user.

@pytest.fixture()
def logged_in_user(app):
    """
    Creates a bare user with no expenses and returns (client, user_id).
    The client is already authenticated as that user.
    """
    conn = db_module.get_db()
    from werkzeug.security import generate_password_hash
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            "Add User",
            "adduser@example.com",
            generate_password_hash("password123"),
            "2026-01-01 08:00:00",
        ),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    client = app.test_client()
    _login_as(client, user_id)
    return client, user_id


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_get_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated GET /expenses/add must redirect (302) to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Unauthenticated GET /expenses/add must redirect with 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_post_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated POST /expenses/add must redirect (302) to /login."""
        response = client.post("/expenses/add", data={
            "amount": "10.00",
            "category": "Food",
            "date": "2026-05-01",
            "description": "lunch",
        })
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/add must redirect with 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_post_does_not_insert_row(self, client):
        """A rejected unauthenticated POST must not write any expense to the DB."""
        conn = db_module.get_db()
        try:
            before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()

        client.post("/expenses/add", data={
            "amount": "10.00",
            "category": "Food",
            "date": "2026-05-01",
            "description": "lunch",
        })

        conn = db_module.get_db()
        try:
            after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()

        assert after == before, (
            "Unauthenticated POST must not insert any rows into expenses"
        )


# ---------------------------------------------------------------------------
# 2. GET — Form rendering
# ---------------------------------------------------------------------------

class TestGetForm:
    def test_authenticated_get_returns_200(self, logged_in_user):
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        assert response.status_code == 200, (
            "Authenticated GET /expenses/add must return 200"
        )

    def test_form_has_amount_input(self, logged_in_user):
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        assert b"amount" in response.data, (
            "Add-expense form must contain an amount input"
        )

    def test_form_has_category_input(self, logged_in_user):
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        assert b"category" in response.data, (
            "Add-expense form must contain a category field"
        )

    def test_form_has_date_input(self, logged_in_user):
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        assert b"date" in response.data, (
            "Add-expense form must contain a date input"
        )

    def test_form_has_description_input(self, logged_in_user):
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        assert b"description" in response.data, (
            "Add-expense form must contain a description field"
        )

    def test_form_posts_to_expenses_add(self, logged_in_user):
        """The form's action must point to /expenses/add (POST method)."""
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        assert b"/expenses/add" in response.data, (
            "Form action must point to /expenses/add"
        )

    def test_all_7_categories_present(self, logged_in_user):
        """The category dropdown must contain all 7 fixed categories."""
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        data = response.data
        expected_categories = [
            b"Food", b"Transport", b"Bills", b"Health",
            b"Entertainment", b"Shopping", b"Other",
        ]
        for category in expected_categories:
            assert category in data, (
                f"Category {category.decode()} must appear in the dropdown"
            )

    def test_exactly_7_categories_no_extras(self, logged_in_user):
        """
        The dropdown must contain exactly the 7 fixed categories —
        no extras beyond the spec-defined list.
        """
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        data = response.data.decode("utf-8")
        fixed_categories = [
            "Food", "Transport", "Bills", "Health",
            "Entertainment", "Shopping", "Other",
        ]
        # All 7 must appear
        for cat in fixed_categories:
            assert cat in data, f"Category '{cat}' must be in the dropdown"

    def test_page_extends_base_html(self, logged_in_user):
        """
        All templates extend base.html which includes nav/footer landmarks.
        The add-expense page must include at least one element from base.html.
        """
        client, _ = logged_in_user
        response = client.get("/expenses/add")
        # base.html renders the nav; check for a common landmark it provides
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data, (
            "Add-expense page must render a full HTML document (extends base.html)"
        )


# ---------------------------------------------------------------------------
# 3. POST — Happy path
# ---------------------------------------------------------------------------

class TestPostHappyPath:
    def test_valid_post_redirects_to_profile(self, logged_in_user):
        """A successful form submission must redirect (302) to /profile."""
        client, _ = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "25.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Dinner",
        })
        assert response.status_code == 302, (
            "Successful POST must redirect with 302"
        )
        assert "/profile" in response.headers["Location"], (
            "Successful POST must redirect to /profile"
        )

    def test_valid_post_inserts_one_row(self, logged_in_user):
        """A successful POST must insert exactly one row into the expenses table."""
        client, user_id = logged_in_user
        before = _count_expenses(user_id)
        client.post("/expenses/add", data={
            "amount": "25.50",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Dinner",
        })
        after = _count_expenses(user_id)
        assert after == before + 1, (
            "Successful POST must insert exactly one expense row"
        )

    def test_valid_post_stores_correct_amount(self, logged_in_user):
        """The inserted expense must store the submitted amount as a float."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "99.99",
            "category": "Transport",
            "date": "2026-05-02",
            "description": "Taxi",
        })
        row = _get_latest_expense(user_id)
        assert row is not None, "An expense row must exist after successful POST"
        assert row["amount"] == pytest.approx(99.99), (
            "Inserted expense amount must match submitted value"
        )

    def test_valid_post_stores_correct_category(self, logged_in_user):
        """The inserted expense must store the selected category."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Bills",
            "date": "2026-05-03",
            "description": "Electricity",
        })
        row = _get_latest_expense(user_id)
        assert row["category"] == "Bills", (
            "Inserted expense category must match submitted value"
        )

    def test_valid_post_stores_correct_date(self, logged_in_user):
        """The inserted expense must store the submitted date."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "50.00",
            "category": "Shopping",
            "date": "2026-04-15",
            "description": "Shoes",
        })
        row = _get_latest_expense(user_id)
        assert row["date"] == "2026-04-15", (
            "Inserted expense date must match submitted value"
        )

    def test_valid_post_stores_correct_description(self, logged_in_user):
        """The inserted expense must store the submitted description."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "8.00",
            "category": "Food",
            "date": "2026-05-04",
            "description": "Coffee at work",
        })
        row = _get_latest_expense(user_id)
        assert row["description"] == "Coffee at work", (
            "Inserted expense description must match submitted value"
        )

    def test_valid_post_stores_correct_user_id(self, logged_in_user):
        """The inserted expense must be owned by the logged-in user."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "30.00",
            "category": "Health",
            "date": "2026-05-05",
            "description": "Pharmacy",
        })
        row = _get_latest_expense(user_id)
        assert row["user_id"] == user_id, (
            "Inserted expense must be attributed to the logged-in user"
        )

    def test_success_flash_message_visible_on_profile(self, logged_in_user):
        """After successful add, the profile page must show a success flash message."""
        client, _ = logged_in_user
        response = client.post(
            "/expenses/add",
            data={
                "amount": "12.00",
                "category": "Entertainment",
                "date": "2026-05-06",
                "description": "Movie",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200, (
            "Following the redirect must yield a 200 from /profile"
        )
        # The spec says: flash("Expense added successfully.", "success")
        assert b"Expense added successfully" in response.data, (
            "A success flash message must be visible on the profile page after add"
        )

    def test_new_expense_appears_on_profile_page(self, logged_in_user):
        """After successful add, the new expense description must appear on /profile."""
        client, _ = logged_in_user
        client.post("/expenses/add", data={
            "amount": "44.00",
            "category": "Other",
            "date": "2026-05-07",
            "description": "Unique gift item xyz",
        })
        profile = client.get("/profile")
        assert b"Unique gift item xyz" in profile.data, (
            "Newly added expense must appear in the transactions list on /profile"
        )

    def test_all_category_values_accepted(self, logged_in_user):
        """Every one of the 7 fixed categories must be accepted and stored correctly."""
        client, user_id = logged_in_user
        categories = [
            "Food", "Transport", "Bills", "Health",
            "Entertainment", "Shopping", "Other",
        ]
        for i, cat in enumerate(categories):
            response = client.post("/expenses/add", data={
                "amount": f"{(i + 1) * 10}.00",
                "category": cat,
                "date": f"2026-05-{i + 1:02d}",
                "description": f"Test {cat}",
            })
            assert response.status_code == 302, (
                f"Category '{cat}' must be accepted and result in a 302 redirect"
            )


# ---------------------------------------------------------------------------
# 4. POST — Blank description stored as NULL
# ---------------------------------------------------------------------------

class TestBlankDescription:
    def test_blank_description_returns_302(self, logged_in_user):
        """Submitting without a description must succeed (302)."""
        client, _ = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "20.00",
            "category": "Food",
            "date": "2026-05-08",
            "description": "",
        })
        assert response.status_code == 302, (
            "Blank description must still result in a successful 302 redirect"
        )

    def test_blank_description_stored_as_null(self, logged_in_user):
        """A blank description must be stored as NULL (Python None) in the DB."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "20.00",
            "category": "Food",
            "date": "2026-05-08",
            "description": "",
        })
        row = _get_latest_expense(user_id)
        assert row["description"] is None, (
            "Blank description must be stored as NULL in the database"
        )

    def test_whitespace_only_description_stored_as_null(self, logged_in_user):
        """A whitespace-only description must also be stored as NULL."""
        client, user_id = logged_in_user
        client.post("/expenses/add", data={
            "amount": "20.00",
            "category": "Food",
            "date": "2026-05-09",
            "description": "   ",
        })
        row = _get_latest_expense(user_id)
        assert row["description"] is None, (
            "Whitespace-only description must be stored as NULL, not a blank string"
        )


# ---------------------------------------------------------------------------
# 5. POST — Blank date defaults to today
# ---------------------------------------------------------------------------

class TestDefaultDate:
    def test_blank_date_returns_302(self, logged_in_user):
        """Submitting without a date must succeed (302) — defaults to today."""
        client, _ = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "5.00",
            "category": "Food",
            "date": "",
            "description": "Quick snack",
        })
        assert response.status_code == 302, (
            "Blank date must default to today and result in a 302 redirect"
        )

    def test_blank_date_defaults_to_today(self, logged_in_user):
        """When date is omitted, the stored date must equal today's ISO date."""
        client, user_id = logged_in_user
        today = date.today().isoformat()
        client.post("/expenses/add", data={
            "amount": "5.00",
            "category": "Food",
            "date": "",
            "description": "Quick snack",
        })
        row = _get_latest_expense(user_id)
        assert row["date"] == today, (
            f"Blank date must default to today ({today}), got: {row['date']}"
        )

    def test_blank_date_inserts_one_row(self, logged_in_user):
        """Blank date must not prevent the row from being inserted."""
        client, user_id = logged_in_user
        before = _count_expenses(user_id)
        client.post("/expenses/add", data={
            "amount": "5.00",
            "category": "Food",
            "date": "",
            "description": "",
        })
        after = _count_expenses(user_id)
        assert after == before + 1, (
            "Blank date must result in exactly one new expense row"
        )


# ---------------------------------------------------------------------------
# 6. POST — Amount validation errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_amount", [
    "abc",
    "not-a-number",
    "",
    "   ",
    "12abc",
    "1,000",        # comma-separated — not a valid float literal
    "$50",
])
def test_non_numeric_amount_shows_error(logged_in_user, bad_amount):
    """Non-numeric amount values must re-render the form with an error (200)."""
    client, user_id = logged_in_user
    before = _count_expenses(user_id)
    response = client.post("/expenses/add", data={
        "amount": bad_amount,
        "category": "Food",
        "date": "2026-05-01",
        "description": "test",
    })
    assert response.status_code == 200, (
        f"Non-numeric amount {bad_amount!r} must re-render the form (200), not redirect"
    )
    after = _count_expenses(user_id)
    assert after == before, (
        f"Non-numeric amount {bad_amount!r} must not insert any expense row"
    )


@pytest.mark.parametrize("zero_or_negative", [
    "0",
    "0.00",
    "-1",
    "-0.01",
    "-100.00",
    "-99999",
])
def test_zero_or_negative_amount_shows_error(logged_in_user, zero_or_negative):
    """Zero or negative amount values must re-render the form with an error (200)."""
    client, user_id = logged_in_user
    before = _count_expenses(user_id)
    response = client.post("/expenses/add", data={
        "amount": zero_or_negative,
        "category": "Food",
        "date": "2026-05-01",
        "description": "test",
    })
    assert response.status_code == 200, (
        f"Amount {zero_or_negative!r} must re-render the form (200), not redirect"
    )
    after = _count_expenses(user_id)
    assert after == before, (
        f"Amount {zero_or_negative!r} must not insert any expense row"
    )


def test_amount_error_message_visible(logged_in_user):
    """When an invalid amount is submitted, an error message must appear in the response."""
    client, _ = logged_in_user
    response = client.post("/expenses/add", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-05-01",
        "description": "test",
    })
    data = response.data.decode("utf-8")
    # The spec mandates an inline error — check for generic error indicator
    assert "error" in data.lower() or "invalid" in data.lower() or "valid number" in data.lower(), (
        "An error message must appear when a non-numeric amount is submitted"
    )


def test_zero_amount_error_message_visible(logged_in_user):
    """When amount <= 0 is submitted, an error message must appear."""
    client, _ = logged_in_user
    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-05-01",
        "description": "test",
    })
    data = response.data.decode("utf-8")
    assert "error" in data.lower() or "zero" in data.lower() or "greater" in data.lower(), (
        "An error message must appear when amount is 0 or negative"
    )


# ---------------------------------------------------------------------------
# 7. POST — Date validation errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_date", [
    "not-a-date",
    "99-99-9999",
    "2026/05/01",       # wrong separator
    "05-01-2026",       # MM-DD-YYYY (wrong order)
    "2026-13-01",       # month 13 doesn't exist
    "2026-00-01",       # month 0 doesn't exist
    "2026-04-31",       # April has no 31st
    "abcd-ef-gh",
    "today",
])
def test_invalid_date_shows_error(logged_in_user, bad_date):
    """An invalid date string must re-render the form with an error (200)."""
    client, user_id = logged_in_user
    before = _count_expenses(user_id)
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": bad_date,
        "description": "test",
    })
    assert response.status_code == 200, (
        f"Invalid date {bad_date!r} must re-render the form (200), not redirect"
    )
    after = _count_expenses(user_id)
    assert after == before, (
        f"Invalid date {bad_date!r} must not insert any expense row"
    )


def test_invalid_date_error_message_visible(logged_in_user):
    """When an invalid date is submitted, an error message must appear."""
    client, _ = logged_in_user
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": "not-a-date",
        "description": "test",
    })
    data = response.data.decode("utf-8")
    assert "error" in data.lower() or "valid date" in data.lower() or "date" in data.lower(), (
        "An error message mentioning the date must appear for an invalid date"
    )


# ---------------------------------------------------------------------------
# 8. POST — Category validation error
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_category", [
    "Groceries",
    "Rent",
    "",
    "FOOD",            # case-sensitive mismatch
    "food",
    "transport",
    "<script>alert(1)</script>",
])
def test_invalid_category_shows_error(logged_in_user, bad_category):
    """An unrecognised category must re-render the form with an error (200)."""
    client, user_id = logged_in_user
    before = _count_expenses(user_id)
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": bad_category,
        "date": "2026-05-01",
        "description": "test",
    })
    assert response.status_code == 200, (
        f"Invalid category {bad_category!r} must re-render the form (200), not redirect"
    )
    after = _count_expenses(user_id)
    assert after == before, (
        f"Invalid category {bad_category!r} must not insert any expense row"
    )


# ---------------------------------------------------------------------------
# 9. POST — Form input preserved on validation error
# ---------------------------------------------------------------------------

class TestFormInputPreservedOnError:
    def test_amount_preserved_on_invalid_date(self, logged_in_user):
        """On validation failure, the submitted amount must be echoed back."""
        client, _ = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "77.77",
            "category": "Food",
            "date": "not-a-date",
            "description": "preserved test",
        })
        assert b"77.77" in response.data, (
            "Submitted amount must be preserved in the re-rendered form on error"
        )

    def test_description_preserved_on_invalid_amount(self, logged_in_user):
        """On validation failure, the submitted description must be echoed back."""
        client, _ = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-05-01",
            "description": "my special description",
        })
        assert b"my special description" in response.data, (
            "Submitted description must be preserved in the re-rendered form on error"
        )


# ---------------------------------------------------------------------------
# 10. User data isolation — expense belongs to the correct user
# ---------------------------------------------------------------------------

class TestUserIsolation:
    def test_expense_not_visible_to_other_user(self, app, logged_in_user):
        """
        An expense added by user A must not appear on user B's profile page.
        """
        from werkzeug.security import generate_password_hash

        # Create user B with no expenses
        conn = db_module.get_db()
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (
                "User B",
                "userb@example.com",
                generate_password_hash("password123"),
                "2026-01-02 09:00:00",
            ),
        )
        user_b_id = cur.lastrowid
        conn.commit()
        conn.close()

        # User A adds an expense with a unique description
        client_a, _ = logged_in_user
        client_a.post("/expenses/add", data={
            "amount": "123.45",
            "category": "Other",
            "date": "2026-05-10",
            "description": "user_a_unique_purchase_xyz",
        })

        # User B logs in and checks their profile
        client_b = app.test_client()
        _login_as(client_b, user_b_id)
        profile_b = client_b.get("/profile")
        assert b"user_a_unique_purchase_xyz" not in profile_b.data, (
            "User B must not see User A's expenses on their profile page"
        )

    def test_two_users_see_own_totals_independently(self, app, logged_in_user):
        """
        Adding an expense for user A must not change user B's total on /profile.
        """
        from werkzeug.security import generate_password_hash

        # Create user B with one known expense
        conn = db_module.get_db()
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (
                "User C",
                "userc@example.com",
                generate_password_hash("password123"),
                "2026-01-03 10:00:00",
            ),
        )
        user_c_id = cur.lastrowid
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_c_id, 10.00, "Food", "2026-05-01", "User C lunch"),
        )
        conn.commit()
        conn.close()

        # User A adds an expense
        client_a, _ = logged_in_user
        client_a.post("/expenses/add", data={
            "amount": "999.00",
            "category": "Shopping",
            "date": "2026-05-02",
            "description": "User A big purchase",
        })

        # User C's total on /profile must still be only their own 10.00
        client_c = app.test_client()
        _login_as(client_c, user_c_id)
        profile_c = client_c.get("/profile")
        assert b"10.00" in profile_c.data, (
            "User C's profile must still show their own total (10.00) unaffected by user A"
        )
        assert b"999.00" not in profile_c.data, (
            "User A's 999.00 expense must not appear on User C's profile"
        )


# ---------------------------------------------------------------------------
# 11. Edge cases — SQL injection and boundary values
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_sql_injection_in_description_stored_safely(self, logged_in_user):
        """
        A SQL injection payload in the description field must be stored as
        a literal string (parameterized queries prevent injection).
        """
        client, user_id = logged_in_user
        payload = "'; DROP TABLE expenses; --"
        response = client.post("/expenses/add", data={
            "amount": "5.00",
            "category": "Food",
            "date": "2026-05-01",
            "description": payload,
        })
        # The insert must succeed (302) and the expenses table must still exist
        assert response.status_code == 302, (
            "SQL injection in description must not crash the route"
        )
        conn = db_module.get_db()
        try:
            count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
            assert count > 0, (
                "expenses table must still exist after SQL injection attempt in description"
            )
        finally:
            conn.close()

    def test_very_large_valid_amount_accepted(self, logged_in_user):
        """A large but valid positive float must be accepted."""
        client, user_id = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "999999.99",
            "category": "Bills",
            "date": "2026-05-01",
            "description": "Large bill",
        })
        assert response.status_code == 302, (
            "A very large valid amount must be accepted and result in 302 redirect"
        )
        row = _get_latest_expense(user_id)
        assert row["amount"] == pytest.approx(999999.99), (
            "Large amount must be stored with full precision"
        )

    def test_minimum_positive_amount_accepted(self, logged_in_user):
        """A very small positive float (0.01) must be accepted."""
        client, user_id = logged_in_user
        response = client.post("/expenses/add", data={
            "amount": "0.01",
            "category": "Food",
            "date": "2026-05-01",
            "description": "Penny",
        })
        assert response.status_code == 302, (
            "Minimum positive amount 0.01 must be accepted"
        )
        row = _get_latest_expense(user_id)
        assert row["amount"] == pytest.approx(0.01), (
            "Minimum amount 0.01 must be stored correctly"
        )

    def test_multiple_sequential_adds_all_stored(self, logged_in_user):
        """Multiple sequential expense additions must each insert a distinct row."""
        client, user_id = logged_in_user
        expenses_to_add = [
            ("10.00", "Food",      "2026-05-01", "First"),
            ("20.00", "Transport", "2026-05-02", "Second"),
            ("30.00", "Bills",     "2026-05-03", "Third"),
        ]
        for amount, category, exp_date, description in expenses_to_add:
            response = client.post("/expenses/add", data={
                "amount": amount,
                "category": category,
                "date": exp_date,
                "description": description,
            })
            assert response.status_code == 302

        assert _count_expenses(user_id) == len(expenses_to_add), (
            "Each sequential expense add must persist a separate row in the DB"
        )
