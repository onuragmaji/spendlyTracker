from datetime import datetime

from database.db import get_db


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


def get_summary_stats(user_id):
    db = get_db()
    try:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0.0), COUNT(*) FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        total_spent = float(row[0])
        transaction_count = int(row[1])

        top_row = db.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        return {
            "total_spent":       total_spent,
            "transaction_count": transaction_count,
            "top_category":      top_row[0] if top_row is not None else "—",
        }
    finally:
        db.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT date, description, category, amount
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (user_id, limit),
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


def get_category_breakdown(user_id):
    db = get_db()
    try:
        cursor = db.execute(
            "SELECT category AS name, SUM(amount) AS amount "
            "FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY amount DESC",
            (user_id,),
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
