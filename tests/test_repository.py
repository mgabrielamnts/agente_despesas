from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models import Expense
import src.repository as repository


@pytest.fixture
def memory_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(repository, "SessionLocal", TestSession)
    yield TestSession
    Base.metadata.drop_all(bind=engine)


def expense_data():
    return {
        "amount": 42.50,
        "category": "Alimentação",
        "expense_date": "2026-10-03",
        "description": "Almoço",
        "establishment": "Restaurante",
    }


def test_repository_crud_with_in_memory_sqlite(memory_session):
    created = repository.add_expense(expense_data(), raw_text="gastei 42,50 no almoço")
    assert created.id is not None

    expenses = repository.list_expenses()
    assert len(expenses) == 1
    assert float(expenses[0].amount) == 42.50

    updated = repository.update_expense(
        created.id,
        {
            **expense_data(),
            "amount": 50.0,
            "description": "Jantar",
        },
    )
    assert updated is True

    expenses = repository.list_expenses()
    assert float(expenses[0].amount) == 50.0
    assert expenses[0].description == "Jantar"

    deleted = repository.delete_expense(created.id)
    assert deleted is True
    assert repository.list_expenses() == []


def test_anomaly_review_is_persisted(memory_session):
    created = repository.add_expense(expense_data())
    repository.mark_anomaly_reviewed(created.id, "confirmed")
    assert created.id in repository.reviewed_anomaly_ids()


def test_migrates_old_bills_category(memory_session):
    data = {**expense_data(), "category": "Contas"}
    created = repository.add_expense(data)
    repository.migrate_category_labels()
    migrated = next(e for e in repository.list_expenses() if e.id == created.id)
    assert migrated.category == "Contas pessoais"
