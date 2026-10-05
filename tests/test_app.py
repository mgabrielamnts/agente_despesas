import os
from pathlib import Path
import subprocess
import sys


APP_TEST_SCRIPT = r"""
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

database_path = os.environ["APP_TEST_DB"]
os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
os.environ["APP_TIMEZONE"] = "America/Sao_Paulo"

from streamlit.testing.v1 import AppTest

app = AppTest.from_file("app.py", default_timeout=20)
app.run()
assert len(app.exception) == 0, app.exception

today = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
with sqlite3.connect(database_path) as connection:
    connection.execute(
        '''
        INSERT INTO expenses
            (amount, category, expense_date, description, establishment, raw_text)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (42.50, "Alimentação", today, "Almoço", "Restaurante", None),
    )
    connection.commit()

app.run()
assert len(app.exception) == 0, app.exception
"""


def test_streamlit_app_starts_with_dashboard_data(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["APP_TEST_DB"] = str(tmp_path / "app_test.db")

    result = subprocess.run(
        [sys.executable, "-c", APP_TEST_SCRIPT],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
