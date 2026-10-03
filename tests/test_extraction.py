from datetime import date

import pytest

from src.extraction import (
    ExtractionError,
    _validate_partial,
    merge_expense_data,
    missing_fields,
)


REFERENCE_DATE = date(2026, 10, 3)


def test_validate_valid_expense():
    data = {
        "amount": 32.50,
        "category": "Alimentação",
        "expense_date": "2026-10-01",
        "description": "Almoço",
        "establishment": "iFood",
    }
    result = _validate_partial(data, reference_date=REFERENCE_DATE)
    assert result["amount"] == 32.50
    assert result["expense_date"] == "2026-10-01"


def test_validate_rejects_negative_amount():
    data = {
        "amount": -10,
        "category": "Outros",
        "expense_date": "2026-10-01",
        "description": "Teste",
        "establishment": None,
    }
    with pytest.raises(ExtractionError):
        _validate_partial(data, reference_date=REFERENCE_DATE)


def test_merge_expense_data_preserves_previous_fields():
    previous = {
        "amount": 50.0,
        "category": "Transporte",
        "expense_date": "2026-10-02",
        "description": "gasolina",
        "establishment": None,
    }
    new = {
        "amount": 65.0,
        "category": None,
        "expense_date": None,
        "description": None,
        "establishment": None,
    }
    result = merge_expense_data(previous, new)
    assert result["amount"] == 65.0
    assert result["category"] == "Transporte"
    assert result["description"] == "gasolina"
    assert result["expense_date"] == "2026-10-02"


def test_missing_fields_detects_incomplete_expense():
    data = {
        "amount": 87.0,
        "category": "Compras",
        "expense_date": None,
        "description": None,
        "establishment": None,
    }
    assert missing_fields(data) == ["description", "expense_date"]


def test_validate_rejects_far_future_date():
    data = {
        "amount": 10,
        "category": "Outros",
        "expense_date": "2027-01-01",
        "description": "Teste",
        "establishment": None,
    }
    with pytest.raises(ExtractionError):
        _validate_partial(data, reference_date=REFERENCE_DATE)


def test_validate_rejects_text_above_database_limit():
    data = {
        "amount": 10,
        "category": "Outros",
        "expense_date": "2026-10-03",
        "description": "x" * 201,
        "establishment": None,
    }
    with pytest.raises(ExtractionError):
        _validate_partial(data, reference_date=REFERENCE_DATE)
