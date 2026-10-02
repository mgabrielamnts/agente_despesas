from datetime import date
import pytest
from src.extraction import ExtractionError, _validate

def test_validate_valid_expense():
    data={"amount":32.50,"category":"Alimentação","expense_date":"2026-10-01","description":"Almoço","establishment":"iFood"}
    result=_validate(data); assert result["amount"]==32.50; assert date.fromisoformat(result["expense_date"])

def test_validate_rejects_negative_amount():
    data={"amount":-10,"category":"Outros","expense_date":"2026-10-01","description":"Teste","establishment":None}
    with pytest.raises(ExtractionError): _validate(data)
