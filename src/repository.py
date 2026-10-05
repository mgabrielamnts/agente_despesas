from datetime import date
from decimal import Decimal

from sqlalchemy import select, update

from src.database import SessionLocal
from src.models import AnomalyReview, Expense
from src.time_utils import local_today
from src.validation import validate_expense_data


def add_expense(data: dict) -> Expense:
    validated = validate_expense_data(data, reference_date=local_today())
    expense = Expense(
        amount=Decimal(str(validated["amount"])),
        category=validated["category"],
        expense_date=date.fromisoformat(validated["expense_date"]),
        description=validated["description"],
        establishment=validated.get("establishment"),
    )
    with SessionLocal() as session:
        try:
            session.add(expense)
            session.commit()
            session.refresh(expense)
            return expense
        except Exception:
            session.rollback()
            raise


def list_expenses() -> list[Expense]:
    with SessionLocal() as session:
        stmt = select(Expense).order_by(Expense.expense_date.desc(), Expense.id.desc())
        return list(session.scalars(stmt).all())


def update_expense(expense_id: int, data: dict) -> bool:
    validated = validate_expense_data(data, reference_date=local_today())
    with SessionLocal() as session:
        expense = session.get(Expense, expense_id)
        if expense is None:
            return False

        expense.amount = Decimal(str(validated["amount"]))
        expense.category = validated["category"]
        expense.expense_date = date.fromisoformat(validated["expense_date"])
        expense.description = validated["description"]
        expense.establishment = validated.get("establishment") or None

        review = session.scalar(
            select(AnomalyReview).where(AnomalyReview.expense_id == expense_id)
        )
        if review is not None:
            session.delete(review)

        session.commit()
        return True


def delete_expense(expense_id: int) -> bool:
    with SessionLocal() as session:
        expense = session.get(Expense, expense_id)
        if expense is None:
            return False
        session.delete(expense)
        session.commit()
        return True


def mark_anomaly_reviewed(expense_id: int, status: str = "confirmed") -> None:
    with SessionLocal() as session:
        review = session.scalar(
            select(AnomalyReview).where(AnomalyReview.expense_id == expense_id)
        )
        if review is None:
            session.add(AnomalyReview(expense_id=expense_id, status=status))
        else:
            review.status = status
        session.commit()


def reviewed_anomaly_ids() -> set[int]:
    with SessionLocal() as session:
        return set(session.scalars(select(AnomalyReview.expense_id)).all())


def migrate_category_labels() -> None:
    """Keep existing local databases compatible with renamed labels."""
    with SessionLocal() as session:
        session.execute(
            update(Expense)
            .where(Expense.category == "Contas")
            .values(category="Contas pessoais")
        )
        session.commit()
