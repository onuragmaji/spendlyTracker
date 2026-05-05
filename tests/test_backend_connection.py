import pytest
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


class TestGetUserById:
    def test_valid_user_returns_dict(self, seed_user):
        result = get_user_by_id(seed_user)
        assert result is not None
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert "member_since" in result

    def test_member_since_format(self, seed_user):
        result = get_user_by_id(seed_user)
        assert result["member_since"] == "January 2026"

    def test_nonexistent_id_returns_none(self, app):
        result = get_user_by_id(99999)
        assert result is None


class TestGetSummaryStats:
    def test_with_expenses(self, seed_user):
        result = get_summary_stats(seed_user)
        assert result["total_spent"] == pytest.approx(100.00)
        assert result["transaction_count"] == 3
        assert result["top_category"] == "Bills"

    def test_empty_user(self, empty_user):
        result = get_summary_stats(empty_user)
        assert result["total_spent"] == 0
        assert result["transaction_count"] == 0
        assert result["top_category"] == "—"

    def test_returns_required_keys(self, seed_user):
        result = get_summary_stats(seed_user)
        assert set(result.keys()) == {"total_spent", "transaction_count", "top_category"}


class TestGetRecentTransactions:
    def test_ordered_newest_first(self, seed_user):
        result = get_recent_transactions(seed_user)
        dates = [tx["date"] for tx in result]
        assert dates == sorted(dates, reverse=True)

    def test_correct_keys(self, seed_user):
        result = get_recent_transactions(seed_user)
        for tx in result:
            assert set(tx.keys()) == {"date", "description", "category", "amount"}

    def test_limit_respected(self, seed_user):
        result = get_recent_transactions(seed_user, limit=2)
        assert len(result) == 2

    def test_empty_user_returns_empty_list(self, empty_user):
        result = get_recent_transactions(empty_user)
        assert result == []


class TestGetCategoryBreakdown:
    def test_pct_sums_to_100(self, seed_user):
        result = get_category_breakdown(seed_user)
        assert sum(item["pct"] for item in result) == 100

    def test_ordered_by_amount_desc(self, seed_user):
        result = get_category_breakdown(seed_user)
        amounts = [item["amount"] for item in result]
        assert amounts == sorted(amounts, reverse=True)

    def test_correct_keys(self, seed_user):
        result = get_category_breakdown(seed_user)
        for item in result:
            assert set(item.keys()) == {"name", "amount", "pct"}

    def test_pct_are_integers(self, seed_user):
        result = get_category_breakdown(seed_user)
        for item in result:
            assert isinstance(item["pct"], int)

    def test_empty_user_returns_empty_list(self, empty_user):
        result = get_category_breakdown(empty_user)
        assert result == []

    def test_category_percentages(self, seed_user):
        result = get_category_breakdown(seed_user)
        breakdown = {item["name"]: item for item in result}
        assert breakdown["Bills"]["pct"] == 75
        assert breakdown["Food"]["pct"] == 25


class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_authenticated_returns_200(self, client, seed_user):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user
        response = client.get("/profile")
        assert response.status_code == 200

    def test_shows_user_name(self, client, seed_user):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user
        response = client.get("/profile")
        assert b"Test User" in response.data

    def test_shows_user_email(self, client, seed_user):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user
        response = client.get("/profile")
        assert b"test@example.com" in response.data

    def test_shows_rupee_symbol(self, client, seed_user):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user
        response = client.get("/profile")
        assert "₹".encode() in response.data

    def test_total_spent_correct(self, client, seed_user):
        with client.session_transaction() as sess:
            sess["user_id"] = seed_user
        response = client.get("/profile")
        assert b"100.00" in response.data

    def test_empty_user_no_errors(self, client, empty_user):
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user
        response = client.get("/profile")
        assert response.status_code == 200
        assert b"0.00" in response.data
