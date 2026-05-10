"""
tests/test_06-date-filter-profile-page.py

Tests for Step 6: Date Filter for Profile Page
Covers the GET /profile route accepting optional from_date / to_date query
parameters and the underlying query helpers in database/queries.py.

Spec reference: .claude/specs/06-date-filter-profile-page.md
"""

import pytest
from werkzeug.security import generate_password_hash

import app as flask_app
import database.db as db_module
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# conftest.py already provides: app, client, seed_user, empty_user.
# The fixtures below add date-filter-specific user scenarios.

@pytest.fixture()
def multi_month_user(app):
    """
    A user with expenses spread across four distinct months so that
    date-range filtering can be verified to include / exclude the right rows.

    Expenses:
      2026-01-10  Food        50.00   January lunch
      2026-02-15  Transport   30.00   February taxi
      2026-03-20  Bills       80.00   March electricity
      2026-04-05  Health      20.00   April pharmacy
      2026-04-25  Shopping    60.00   April shoes

    Totals all-time: 240.00, 5 transactions
    """
    conn = db_module.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            "Multi User",
            "multi@example.com",
            generate_password_hash("password123"),
            "2026-01-01 08:00:00",
        ),
    )
    user_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, 50.00, "Food",      "2026-01-10", "January lunch"),
            (user_id, 30.00, "Transport", "2026-02-15", "February taxi"),
            (user_id, 80.00, "Bills",     "2026-03-20", "March electricity"),
            (user_id, 20.00, "Health",    "2026-04-05", "April pharmacy"),
            (user_id, 60.00, "Shopping",  "2026-04-25", "April shoes"),
        ],
    )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture()
def many_expenses_user(app):
    """
    A user with 12 expenses all in April 2026, used to verify that the
    10-row limit still applies when a date filter is active.
    Expense descriptions are 'Expense 1' through 'Expense 12'.
    """
    conn = db_module.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (
            "Many User",
            "many@example.com",
            generate_password_hash("password123"),
            "2026-01-01 08:00:00",
        ),
    )
    user_id = cur.lastrowid
    rows = [
        (user_id, float(i * 5), "Food", f"2026-04-{i:02d}", f"Expense {i}")
        for i in range(1, 13)  # 12 expenses on 2026-04-01 through 2026-04-12
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return user_id


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _login_as(client, user_id):
    """Inject user_id directly into the Flask test session — no password round-trip."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "Unauthenticated /profile must redirect (302)"
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_with_from_date_redirects_to_login(self, client):
        response = client.get("/profile?from_date=2026-04-01")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_with_both_date_params_redirects_to_login(self, client):
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# 2. All-time view — no regression from Step 5
# ---------------------------------------------------------------------------

class TestAllTimeView:
    def test_returns_200(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert response.status_code == 200, "Authenticated /profile must return 200"

    def test_shows_total_spent_all_time(self, client, seed_user):
        # seed_user has 3 expenses: 75.00 + 20.00 + 5.00 = 100.00
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"100.00" in response.data, "All-time total should be 100.00"

    def test_shows_all_transaction_descriptions(self, client, seed_user):
        # seed_user expenses have descriptions: Electricity, Lunch, Coffee
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"Electricity" in response.data
        assert b"Lunch" in response.data
        assert b"Coffee" in response.data

    def test_no_active_filter_label_when_no_params(self, client, seed_user):
        """The 'Showing:' label must not appear when no date params are given."""
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"Showing:" not in response.data, (
            "Active-filter label must be absent when no date params are provided"
        )

    def test_date_filter_form_has_from_date_input(self, client, seed_user):
        """The filter form must contain a from_date input."""
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"from_date" in response.data, "Filter form must include from_date input"

    def test_date_filter_form_has_to_date_input(self, client, seed_user):
        """The filter form must contain a to_date input."""
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"to_date" in response.data, "Filter form must include to_date input"

    def test_preset_this_month_button_present(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"This Month" in response.data, "'This Month' preset button must be present"

    def test_preset_last_3_months_button_present(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"Last 3 Months" in response.data, "'Last 3 Months' preset button must be present"

    def test_preset_all_time_button_present(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"All Time" in response.data, "'All Time' preset button must be present"

    def test_apply_button_present(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"Apply" in response.data, "Apply submit button must be present"

    def test_form_method_is_get(self, client, seed_user):
        """The filter form must use GET so params appear in the URL."""
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b'method="GET"' in response.data or b"method=GET" in response.data, (
            "Filter form must use GET method"
        )

    def test_date_inputs_are_type_date(self, client, seed_user):
        """HTML5 date inputs must be used — no third-party pickers."""
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b'type="date"' in response.data, (
            "Date inputs must use type=date"
        )


# ---------------------------------------------------------------------------
# 3. Custom date range — both from_date and to_date
# ---------------------------------------------------------------------------

class TestCustomDateRange:
    def test_returns_200_with_valid_range(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert response.status_code == 200

    def test_filter_includes_expenses_in_range(self, client, multi_month_user):
        """Expenses within the range must appear in the transaction list."""
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"April pharmacy" in response.data, "April pharmacy must appear in April filter"
        assert b"April shoes" in response.data, "April shoes must appear in April filter"

    def test_filter_excludes_expenses_outside_range(self, client, multi_month_user):
        """Expenses outside the range must not appear anywhere on the page."""
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"January lunch" not in response.data, "January expense must not appear"
        assert b"February taxi" not in response.data, "February expense must not appear"
        assert b"March electricity" not in response.data, "March expense must not appear"

    def test_filter_total_spent_reflects_range(self, client, multi_month_user):
        """Stats tile 'Total spent' must reflect only expenses in the selected range."""
        # April: Health 20.00 + Shopping 60.00 = 80.00
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"80.00" in response.data, "Filtered total spent should be 80.00"

    def test_filter_category_breakdown_restricted_to_range(self, client, multi_month_user):
        """Category breakdown must only include categories with expenses in the range."""
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"Health" in response.data, "Health must appear in April breakdown"
        assert b"Shopping" in response.data, "Shopping must appear in April breakdown"
        # Out-of-range categories must not appear
        assert b"Transport" not in response.data, "Transport must not appear in April breakdown"
        assert b"Bills" not in response.data, "Bills must not appear in April breakdown"

    def test_inclusive_lower_bound(self, client, multi_month_user):
        """An expense dated exactly on from_date must be included (>= is inclusive)."""
        # April pharmacy is dated 2026-04-05; use from_date=2026-04-05
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-05&to_date=2026-04-30")
        assert b"April pharmacy" in response.data, (
            "Expense on the from_date boundary must be included"
        )

    def test_inclusive_upper_bound(self, client, multi_month_user):
        """An expense dated exactly on to_date must be included (<= is inclusive)."""
        # April shoes is dated 2026-04-25; use to_date=2026-04-25
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-25")
        assert b"April shoes" in response.data, (
            "Expense on the to_date boundary must be included"
        )

    def test_single_day_range_includes_matching_expense(self, client, multi_month_user):
        """When from_date == to_date, only expenses on that exact date are shown."""
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-05&to_date=2026-04-05")
        assert b"April pharmacy" in response.data, "Expense on single-day range must appear"
        assert b"April shoes" not in response.data, "Expense outside single-day range must not appear"

    def test_start_after_end_returns_empty_results(self, client, multi_month_user):
        """
        When from_date > to_date, the SQL WHERE date >= from_date AND date <= to_date
        can match no rows. The page must still return 200 with zero total and no errors.
        """
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-30&to_date=2026-04-01")
        assert response.status_code == 200, (
            "start > end must return 200, not an error"
        )
        assert b"0.00" in response.data, (
            "start > end means no matching rows, so total spent must be 0.00"
        )


# ---------------------------------------------------------------------------
# 4. Only from_date provided (open upper bound)
# ---------------------------------------------------------------------------

class TestFromDateOnly:
    def test_from_date_only_returns_200(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-03-01")
        assert response.status_code == 200

    def test_from_date_only_excludes_earlier_expenses(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-03-01")
        assert b"January lunch" not in response.data
        assert b"February taxi" not in response.data

    def test_from_date_only_includes_on_and_after_from_date(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-03-01")
        assert b"March electricity" in response.data
        assert b"April pharmacy" in response.data
        assert b"April shoes" in response.data

    def test_from_date_only_shows_active_filter_label(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-03-01")
        assert b"Showing:" in response.data, (
            "Active-filter label must appear when from_date is set"
        )


# ---------------------------------------------------------------------------
# 5. Only to_date provided (open lower bound)
# ---------------------------------------------------------------------------

class TestToDateOnly:
    def test_to_date_only_returns_200(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?to_date=2026-02-28")
        assert response.status_code == 200

    def test_to_date_only_excludes_later_expenses(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?to_date=2026-02-28")
        assert b"March electricity" not in response.data
        assert b"April pharmacy" not in response.data
        assert b"April shoes" not in response.data

    def test_to_date_only_includes_on_and_before_to_date(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?to_date=2026-02-28")
        assert b"January lunch" in response.data
        assert b"February taxi" in response.data

    def test_to_date_only_shows_active_filter_label(self, client, multi_month_user):
        _login_as(client, multi_month_user)
        response = client.get("/profile?to_date=2026-02-28")
        assert b"Showing:" in response.data, (
            "Active-filter label must appear when to_date is set"
        )


# ---------------------------------------------------------------------------
# 6. Invalid date formats — silently treated as absent (fall back to all-time)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("from_param,to_param", [
    ("not-a-date", "2026-04-30"),
    ("2026-04-01", "not-a-date"),
    ("not-a-date", "not-a-date"),
    ("2026-99-99", "2026-04-30"),
    ("2026-04-01", "2026-13-01"),
    ("",           ""),
    ("abc",        "xyz"),
    ("2026/04/01", "2026/04/30"),   # wrong separator
    ("04-01-2026", "04-30-2026"),   # wrong order (MM-DD-YYYY)
])
def test_invalid_date_params_return_all_time_data(client, seed_user, from_param, to_param):
    """
    Invalid date strings must be silently discarded; the route must not abort
    or raise. Behavior must fall back to the all-time view.
    seed_user all-time total: 100.00, transaction_count: 3
    """
    _login_as(client, seed_user)
    url = f"/profile?from_date={from_param}&to_date={to_param}"
    response = client.get(url)
    assert response.status_code == 200, (
        f"Invalid params ({from_param!r}, {to_param!r}) must not cause an error"
    )
    # All-time total must appear — confirms invalid params are discarded
    assert b"100.00" in response.data, (
        f"Invalid date params must fall back to all-time data (expected 100.00 total). "
        f"Params: from_date={from_param!r}, to_date={to_param!r}"
    )


# ---------------------------------------------------------------------------
# 7. Empty date range — no expenses match the selected window
# ---------------------------------------------------------------------------

class TestEmptyDateRange:
    def test_empty_range_returns_200(self, client, seed_user):
        """A filter matching no expenses must not raise an error."""
        # seed_user has expenses only in April 2026; 2025-01 has none
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2025-01-01&to_date=2025-01-31")
        assert response.status_code == 200, "Empty date range must return 200"

    def test_empty_range_shows_zero_total_spent(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2025-01-01&to_date=2025-01-31")
        assert b"0.00" in response.data, "Empty range must show 0.00 total spent"

    def test_empty_range_shows_no_transactions_empty_state(self, client, seed_user):
        """When no transactions match the filter, the empty-state message must appear."""
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2025-01-01&to_date=2025-01-31")
        # Template renders: "No transactions recorded yet."
        assert b"No transactions" in response.data, (
            "Empty transaction list must show the no-transactions empty-state message"
        )

    def test_empty_range_shows_no_expenses_in_breakdown(self, client, seed_user):
        """When no expenses match the filter, the breakdown empty-state must appear."""
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2025-01-01&to_date=2025-01-31")
        # Template renders: "No expenses recorded yet."
        assert b"No expenses" in response.data, (
            "Empty breakdown must show the no-expenses empty-state message"
        )

    def test_empty_user_with_any_filter_returns_200(self, client, empty_user):
        """A user with zero expenses must not error regardless of filter params."""
        _login_as(client, empty_user)
        response = client.get("/profile?from_date=2026-01-01&to_date=2026-12-31")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 8. Active-filter label visibility
# ---------------------------------------------------------------------------

class TestActiveFilterLabel:
    def test_label_present_when_both_dates_set(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"Showing:" in response.data, (
            "Active-filter label must appear when both from_date and to_date are set"
        )

    def test_label_contains_from_date(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"2026-04-01" in response.data, (
            "Active-filter label must display the from_date value"
        )

    def test_label_contains_to_date(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"2026-04-30" in response.data, (
            "Active-filter label must display the to_date value"
        )

    def test_label_absent_when_no_params(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b"Showing:" not in response.data, (
            "Active-filter label must not appear when no query params are given"
        )

    def test_label_present_when_only_from_date_set(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01")
        assert b"Showing:" in response.data, (
            "Active-filter label must appear when only from_date is set"
        )

    def test_label_present_when_only_to_date_set(self, client, seed_user):
        _login_as(client, seed_user)
        response = client.get("/profile?to_date=2026-04-30")
        assert b"Showing:" in response.data, (
            "Active-filter label must appear when only to_date is set"
        )


# ---------------------------------------------------------------------------
# 9. Filter input values are preserved after submission
# ---------------------------------------------------------------------------

class TestFilterInputsPreserved:
    def test_from_date_value_preserved_in_input(self, client, seed_user):
        """The from_date input must be pre-filled with the active filter value."""
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b'value="2026-04-01"' in response.data, (
            "from_date value must be pre-filled in the input after form submission"
        )

    def test_to_date_value_preserved_in_input(self, client, seed_user):
        """The to_date input must be pre-filled with the active filter value."""
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b'value="2026-04-30"' in response.data, (
            "to_date value must be pre-filled in the input after form submission"
        )

    def test_no_dates_inputs_have_empty_values(self, client, seed_user):
        """When no filter is active, the date inputs must have empty value attributes."""
        _login_as(client, seed_user)
        response = client.get("/profile")
        assert b'value=""' in response.data, (
            "Date inputs must render with empty value attributes when no filter is active"
        )

    def test_invalid_from_date_not_echoed_back(self, client, seed_user):
        """
        An invalid from_date is silently discarded by the route. It must NOT
        appear as the input's value attribute — the input must remain empty.
        """
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=not-a-date&to_date=2026-04-30")
        assert b'value="not-a-date"' not in response.data, (
            "Invalid from_date must not be echoed back into the input value"
        )

    def test_invalid_to_date_not_echoed_back(self, client, seed_user):
        """An invalid to_date must not be echoed back into the input's value attribute."""
        _login_as(client, seed_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=not-a-date")
        assert b'value="not-a-date"' not in response.data, (
            "Invalid to_date must not be echoed back into the input value"
        )


# ---------------------------------------------------------------------------
# 10. Filter applied consistently across all three sections (stats, transactions,
#     category breakdown)
# ---------------------------------------------------------------------------

class TestFilterConsistency:
    def test_both_april_expenses_appear_as_separate_rows(self, client, multi_month_user):
        """
        The transaction_count in the stats tile must match the number of
        transaction rows rendered in the table for the same date range.
        April has 2 expenses: Health 20 and Shopping 60.
        """
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        data = response.data.decode("utf-8")
        april_rows = data.count("April pharmacy") + data.count("April shoes")
        assert april_rows == 2, "Both April expenses must appear as separate transaction rows"

    def test_breakdown_categories_match_transactions_in_range(self, client, multi_month_user):
        """
        The categories shown in the breakdown must match those in the
        transaction list for the same date range.
        """
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        data = response.data.decode("utf-8")
        # Health and Shopping appear in both transactions and breakdown sections
        assert data.count("Health") >= 2, (
            "Health must appear in both the transaction list and the breakdown"
        )
        assert data.count("Shopping") >= 2, (
            "Shopping must appear in both the transaction list and the breakdown"
        )

    def test_all_sections_exclude_out_of_range_amounts(self, client, multi_month_user):
        """
        Stats, transactions, and breakdown must all exclude amounts from
        expenses outside the selected range — no section must leak data.
        Out-of-range amounts: 50.00 (Jan), 30.00 (Feb), 80.00 (Mar).
        In-range amounts: 20.00 (Apr Health), 60.00 (Apr Shopping), total 80.00.
        """
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        data = response.data.decode("utf-8")
        assert "January lunch" not in data, "January expense must not appear in any section"
        assert "February taxi" not in data, "February expense must not appear in any section"
        assert "March electricity" not in data, "March expense must not appear in any section"
        # Out-of-range monetary values must not appear either
        assert "50.00" not in data, "January amount 50.00 must not appear"
        assert "30.00" not in data, "February amount 30.00 must not appear"
        # NOTE: 80.00 appears as the April total (20+60) so we only check descriptions

    def test_top_category_in_stats_reflects_filtered_range(self, client, multi_month_user):
        """
        The 'Top category' stat tile must reflect the highest-spending category
        within the filter range, not all-time.
        In April: Shopping (60) > Health (20), so top is Shopping.
        """
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert b"Shopping" in response.data, (
            "Top category tile must show Shopping for the April range"
        )


# ---------------------------------------------------------------------------
# 11. 10-row limit still applies within a filtered range
# ---------------------------------------------------------------------------

class TestTransactionLimit:
    def test_limit_10_rows_within_filtered_range(self, client, many_expenses_user):
        """
        Even with a date filter active, get_recent_transactions must return
        at most 10 rows. many_expenses_user has 12 expenses all in April 2026.
        """
        _login_as(client, many_expenses_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        assert response.status_code == 200
        data = response.data.decode("utf-8")
        # Count how many "Expense N" descriptions appear in the rendered page
        rendered_count = sum(1 for i in range(1, 13) if f"Expense {i}" in data)
        assert rendered_count <= 10, (
            f"At most 10 transaction rows must be shown in a filtered range, "
            f"but found {rendered_count}"
        )


# ---------------------------------------------------------------------------
# 12. Data isolation — user cannot see another user's expenses
# ---------------------------------------------------------------------------

class TestUserDataIsolation:
    def test_filter_does_not_return_other_users_expenses(self, client, multi_month_user, seed_user):
        """
        A logged-in user must only see their own expenses, never another user's,
        even when both users have expenses in the same date range.
        seed_user has: Electricity (Bills 75, Apr 08), Lunch (Food 20, Apr 10),
        Coffee (Food 5, Apr 12).
        multi_month_user is logged in and applies an April filter.
        """
        # Log in as multi_month_user
        _login_as(client, multi_month_user)
        response = client.get("/profile?from_date=2026-04-01&to_date=2026-04-30")
        data = response.data.decode("utf-8")
        # seed_user's April expense descriptions must NOT appear
        assert "Electricity" not in data, (
            "Other user's expense description must not leak into filtered results"
        )
        assert "Lunch" not in data, (
            "Other user's expense description must not leak into filtered results"
        )
        assert "Coffee" not in data, (
            "Other user's expense description must not leak into filtered results"
        )

    def test_empty_user_sees_no_other_users_data(self, client, empty_user, seed_user):
        """A user with no expenses must see zero data even if other users have expenses."""
        _login_as(client, empty_user)
        response = client.get("/profile")
        assert b"0.00" in response.data
        assert b"Electricity" not in response.data
        assert b"Lunch" not in response.data


# ---------------------------------------------------------------------------
# 13. Direct query-helper unit tests — get_summary_stats with date params
# ---------------------------------------------------------------------------

class TestQueryHelperSummaryStats:
    """Unit tests for get_summary_stats() with from_date / to_date parameters."""

    def test_both_dates_total_and_count(self, multi_month_user):
        result = get_summary_stats(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert result["total_spent"] == pytest.approx(80.00), (
            "April total (Health 20 + Shopping 60) should be 80.00"
        )
        assert result["transaction_count"] == 2

    def test_from_date_only_total_and_count(self, multi_month_user):
        result = get_summary_stats(multi_month_user, from_date="2026-03-01")
        # March (80) + April (20 + 60) = 160, 3 transactions
        assert result["total_spent"] == pytest.approx(160.00)
        assert result["transaction_count"] == 3

    def test_to_date_only_total_and_count(self, multi_month_user):
        result = get_summary_stats(multi_month_user, to_date="2026-02-28")
        # January (50) + February (30) = 80, 2 transactions
        assert result["total_spent"] == pytest.approx(80.00)
        assert result["transaction_count"] == 2

    def test_no_dates_returns_all_time_data(self, multi_month_user):
        result = get_summary_stats(multi_month_user)
        assert result["total_spent"] == pytest.approx(240.00)
        assert result["transaction_count"] == 5

    def test_empty_range_returns_zero_stats(self, multi_month_user):
        result = get_summary_stats(multi_month_user, from_date="2020-01-01", to_date="2020-12-31")
        assert result["total_spent"] == 0
        assert result["transaction_count"] == 0
        assert result["top_category"] == "—"

    def test_top_category_reflects_filtered_range(self, multi_month_user):
        # In April: Shopping (60) > Health (20), so top category is Shopping
        result = get_summary_stats(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert result["top_category"] == "Shopping"

    def test_returns_required_keys(self, multi_month_user):
        result = get_summary_stats(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert set(result.keys()) == {"total_spent", "transaction_count", "top_category"}

    def test_total_spent_is_float(self, multi_month_user):
        result = get_summary_stats(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert isinstance(result["total_spent"], float)


# ---------------------------------------------------------------------------
# 14. Direct query-helper unit tests — get_recent_transactions with date params
# ---------------------------------------------------------------------------

class TestQueryHelperRecentTransactions:
    """Unit tests for get_recent_transactions() with from_date / to_date parameters."""

    def test_both_dates_returns_correct_transactions(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert len(result) == 2
        descriptions = {tx["description"] for tx in result}
        assert descriptions == {"April pharmacy", "April shoes"}

    def test_from_date_only_returns_on_and_after(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, from_date="2026-03-01")
        assert len(result) == 3  # March + April Health + April Shopping

    def test_to_date_only_returns_on_and_before(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, to_date="2026-02-28")
        assert len(result) == 2  # January + February

    def test_no_dates_returns_all_time_data(self, multi_month_user):
        result = get_recent_transactions(multi_month_user)
        assert len(result) == 5

    def test_empty_range_returns_empty_list(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, from_date="2020-01-01", to_date="2020-12-31")
        assert result == []

    def test_results_ordered_newest_first_with_filter(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, from_date="2026-01-01", to_date="2026-04-30")
        dates = [tx["date"] for tx in result]
        assert dates == sorted(dates, reverse=True), (
            "Filtered results must be ordered newest first"
        )

    def test_limit_applies_within_filtered_range(self, many_expenses_user):
        """The 10-row default limit must apply even within a filtered date range."""
        result = get_recent_transactions(
            many_expenses_user,
            from_date="2026-04-01",
            to_date="2026-04-30",
        )
        assert len(result) <= 10, (
            "get_recent_transactions must return at most 10 rows within the filtered range"
        )

    def test_each_transaction_has_required_keys(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        for tx in result:
            assert set(tx.keys()) == {"date", "description", "category", "amount"}

    def test_amount_is_float(self, multi_month_user):
        result = get_recent_transactions(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        for tx in result:
            assert isinstance(tx["amount"], float)


# ---------------------------------------------------------------------------
# 15. Direct query-helper unit tests — get_category_breakdown with date params
# ---------------------------------------------------------------------------

class TestQueryHelperCategoryBreakdown:
    """Unit tests for get_category_breakdown() with from_date / to_date parameters."""

    def test_both_dates_returns_correct_categories(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert len(result) == 2
        names = {row["name"] for row in result}
        assert names == {"Health", "Shopping"}

    def test_from_date_only_categories(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-03-01")
        # March: Bills; April: Health, Shopping
        names = {row["name"] for row in result}
        assert names == {"Bills", "Shopping", "Health"}

    def test_no_dates_returns_all_categories(self, multi_month_user):
        result = get_category_breakdown(multi_month_user)
        assert len(result) == 5  # Food, Transport, Bills, Health, Shopping

    def test_empty_range_returns_empty_list(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2020-01-01", to_date="2020-12-31")
        assert result == []

    def test_pct_sums_to_100_with_filter(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        assert sum(row["pct"] for row in result) == 100, (
            "Category percentages must sum to exactly 100"
        )

    def test_amounts_match_filtered_expenses(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        by_name = {row["name"]: row for row in result}
        assert by_name["Shopping"]["amount"] == pytest.approx(60.00)
        assert by_name["Health"]["amount"] == pytest.approx(20.00)

    def test_ordered_by_amount_descending_with_filter(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        amounts = [row["amount"] for row in result]
        assert amounts == sorted(amounts, reverse=True), (
            "Breakdown must be ordered by amount descending within the filter"
        )

    def test_pct_values_are_integers(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        for row in result:
            assert isinstance(row["pct"], int)

    def test_each_row_has_required_keys(self, multi_month_user):
        result = get_category_breakdown(multi_month_user, from_date="2026-04-01", to_date="2026-04-30")
        for row in result:
            assert set(row.keys()) == {"name", "amount", "pct"}
