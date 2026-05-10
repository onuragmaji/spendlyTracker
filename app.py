import sqlite3
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import add_expense as db_add_expense, create_user, get_user_by_email, init_db, seed_db
from database.queries import (
    get_user_by_id as queries_get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Please enter your full name.")
    if not email:
        return render_template("register.html", error="Please enter a valid email address.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    password_hash = generate_password_hash(password)
    try:
        create_user(name, email, password_hash)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.")

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Invalid email or password.", email=email)

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


def _valid_date(s):
    try:
        datetime.strptime(s.strip(), "%Y-%m-%d")
        return s.strip()
    except (ValueError, AttributeError):
        return None


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    from_date = _valid_date(request.args.get("from_date", ""))
    to_date   = _valid_date(request.args.get("to_date", ""))

    user         = queries_get_user_by_id(session["user_id"])
    summary      = get_summary_stats(session["user_id"], from_date, to_date)
    transactions = get_recent_transactions(session["user_id"], from_date=from_date, to_date=to_date)
    breakdown    = get_category_breakdown(session["user_id"], from_date, to_date)

    return render_template(
        "profile.html",
        user=user,
        summary=summary,
        transactions=transactions,
        breakdown=breakdown,
        from_date=from_date or "",
        to_date=to_date or "",
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        amount_raw  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        date_raw    = request.form.get("date", "").strip()
        raw_desc    = request.form.get("description", "").strip()
        description = raw_desc or None

        error = None
        amount = None
        date = None

        try:
            amount = float(amount_raw)
            if amount <= 0:
                error = "Amount must be greater than zero."
            elif amount > 1_000_000:
                error = "Amount cannot exceed 1,000,000."
        except ValueError:
            error = "Amount must be a valid number."

        if not error and description and len(description) > 200:
            error = "Description must be 200 characters or fewer."

        if not error and category not in CATEGORIES:
            error = "Please select a valid category."

        if not error:
            if date_raw:
                date = _valid_date(date_raw)
                if date is None:
                    error = "Date must be a valid date (YYYY-MM-DD)."
            else:
                date = datetime.now().strftime("%Y-%m-%d")

        if error:
            return render_template(
                "expenses/add.html",
                error=error,
                categories=CATEGORIES,
                form_data=request.form,
            )

        db_add_expense(session["user_id"], amount, category, date, description)
        flash("Expense added successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("expenses/add.html", categories=CATEGORIES)


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    import os
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
