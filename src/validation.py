from datetime import date, timedelta
import math

from src.config import CATEGORIES


MAX_DESCRIPTION_LENGTH = 200
MAX_ESTABLISHMENT_LENGTH = 120
MAX_FUTURE_DAYS = 1


class ExpenseValidationError(ValueError):
    """Raised when an expense violates application rules."""


def validate_expense_data(
    data: dict,
    reference_date: date,
    *,
    partial: bool = False,
) -> dict:
    """Validate and normalize expense data from any input path.

    The same rules are used for AI extraction, manual forms and repository writes.
    When partial is True, unknown fields are allowed so the conversation can
    collect missing information over multiple turns.
    """
    result = {
        "amount": data.get("amount"),
        "category": data.get("category"),
        "expense_date": data.get("expense_date"),
        "description": data.get("description"),
        "establishment": data.get("establishment"),
    }

    if result["amount"] is not None:
        try:
            amount = float(result["amount"])
        except (TypeError, ValueError) as exc:
            raise ExpenseValidationError("O valor da despesa é inválido.") from exc
        if not math.isfinite(amount) or amount <= 0:
            raise ExpenseValidationError("O valor da despesa deve ser maior que zero.")
        result["amount"] = round(amount, 2)

    if result["category"] is not None:
        result["category"] = str(result["category"]).strip() or None
        if result["category"] and result["category"] not in CATEGORIES:
            raise ExpenseValidationError("A categoria da despesa não é válida.")

    if result["expense_date"] is not None:
        try:
            parsed_date = date.fromisoformat(str(result["expense_date"]))
        except (TypeError, ValueError) as exc:
            raise ExpenseValidationError("A data da despesa é inválida.") from exc
        if parsed_date > reference_date + timedelta(days=MAX_FUTURE_DAYS):
            raise ExpenseValidationError("A data da despesa está muito distante no futuro.")
        result["expense_date"] = parsed_date.isoformat()

    if result["description"] is not None:
        result["description"] = str(result["description"]).strip() or None
        if result["description"] and len(result["description"]) > MAX_DESCRIPTION_LENGTH:
            raise ExpenseValidationError(
                f"A descrição deve ter no máximo {MAX_DESCRIPTION_LENGTH} caracteres."
            )

    if result["establishment"] is not None:
        result["establishment"] = str(result["establishment"]).strip() or None
        if result["establishment"] and len(result["establishment"]) > MAX_ESTABLISHMENT_LENGTH:
            raise ExpenseValidationError(
                f"O estabelecimento deve ter no máximo {MAX_ESTABLISHMENT_LENGTH} caracteres."
            )

    if not partial:
        required = {
            "amount": "Informe o valor da despesa.",
            "category": "Informe a categoria da despesa.",
            "expense_date": "Informe a data da despesa.",
            "description": "Informe a descrição da despesa.",
        }
        for field, message in required.items():
            if result[field] is None:
                raise ExpenseValidationError(message)

    return result
