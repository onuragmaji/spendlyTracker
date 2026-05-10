from datetime import datetime

from database.db import get_db


def _date_clause(user_id, from_date, to_date):
    clause = "WHERE user_id = ?"
    params = [user_id]
    if from_date:
        clause += " AND date >= ?"
        params.append(from_date)
    if to_date:
        clause += " AND date <= ?"
        params.append(to_date)
    return clause, params


def get_user_by_id(user_id):
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    raw = row["created_at"]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            member_since = datetime.strptime(raw, fmt).strftime("%B %Y")
            break
        except ValueError:
            continue
    else:
        member_since = raw

    return {
        "name":         row["name"],
        "email":        row["email"],
        "member_since": member_since,
    }


def get_summary_stats(user_id, from_date=None, to_date=None):
    db = get_db()
    try:
        clause, params = _date_clause(user_id, from_date, to_date)
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0.0), COUNT(*) FROM expenses " + clause,
            params,
        ).fetchone()

        total_spent = float(row[0])
        transaction_count = int(row[1])

        top_row = db.execute(
            "SELECT category FROM expenses " + clause
            + " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
        ).fetchone()

        return {
            "total_spent":       total_spent,
            "transaction_count": transaction_count,
            "top_category":      top_row[0] if top_row is not None else "—",
        }
    finally:
        db.close()


def get_recent_transactions(user_id, limit=10, from_date=None, to_date=None):
    conn = get_db()
    try:
        clause, params = _date_clause(user_id, from_date, to_date)
        cur = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            + clause
            + " ORDER BY date DESC LIMIT ?",
            params + [limit],
        )
        rows = cur.fetchall()
        return [
            {
                "date":        row["date"],
                "description": row["description"],
                "category":    row["category"],
                "amount":      float(row["amount"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_category_breakdown(user_id, from_date=None, to_date=None):
    db = get_db()
    try:
        clause, params = _date_clause(user_id, from_date, to_date)
        cursor = db.execute(
            "SELECT category AS name, SUM(amount) AS amount FROM expenses "
            + clause
            + " GROUP BY category ORDER BY amount DESC",
            params,
        )
        rows = cursor.fetchall()
        if not rows:
            return []
        total = sum(row["amount"] for row in rows)
        result = [
            {
                "name":   row["name"],
                "amount": float(row["amount"]),
                "pct":    round(row["amount"] / total * 100),
            }
            for row in rows
        ]
        diff = 100 - sum(r["pct"] for r in result)
        if diff != 0:
            result[0]["pct"] += diff
        return result
    finally:
        db.close()
