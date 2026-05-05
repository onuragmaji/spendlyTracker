import pytest
from werkzeug.security import generate_password_hash

import app as flask_app
import database.db as db_module


@pytest.fixture()
def app(tmp_path):
    db_file = tmp_path / "test.db"

    original_path = db_module.DB_PATH
    db_module.DB_PATH = str(db_file)

    flask_app.app.config["TESTING"] = True
    flask_app.app.config["SECRET_KEY"] = "test-secret"

    with flask_app.app.app_context():
        db_module.init_db()

    yield flask_app.app

    db_module.DB_PATH = original_path


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seed_user(app):
    conn = db_module.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Test User", "test@example.com",
         generate_password_hash("password123"),
         "2026-01-15 10:00:00"),
    )
    user_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, 75.00, "Bills", "2026-04-08", "Electricity"),
            (user_id, 20.00, "Food",  "2026-04-10", "Lunch"),
            (user_id,  5.00, "Food",  "2026-04-12", "Coffee"),
        ],
    )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture()
def empty_user(app):
    conn = db_module.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Empty User", "empty@example.com",
         generate_password_hash("password123"),
         "2026-02-01 09:00:00"),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id
