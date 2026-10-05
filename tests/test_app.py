import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from streamlit.testing.v1 import AppTest


def test_streamlit_app_starts_with_dashboard_data(monkeypatch, tmp_path):
    database_path = tmp_path / "app_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("APP_TIMEZONE", "America/Sao_Paulo")

    app = AppTest.from_file("app.py", default_timeout=20)
    app.run()
    assert len(app.exception) == 0

    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO expenses
                (amount, category, expense_date, description, establishment, raw_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (42.50, "Alimentação", today, "Almoço", "Restaurante", None),
        )
        connection.commit()

    app.run()
    assert len(app.exception) == 0
