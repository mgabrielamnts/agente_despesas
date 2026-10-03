from datetime import date
from decimal import Decimal

from sqlalchemy import select, update

from src.database import SessionLocal
from src.models import AnomalyReview, Expense


def add_expense(data: dict, raw_text: str | None = None) -> Expense:
    expense = Expense(
        amount=Decimal(str(data["amount"])),
        category=data["category"],
        expense_date=date.fromisoformat(data["expense_date"]),
        description=data["description"],
        establishment=data.get("establishment"),
        raw_text=raw_text,
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
    with SessionLocal() as session:
        expense = session.get(Expense, expense_id)
        if expense is None:
            return False

        expense.amount = Decimal(str(data["amount"]))
        expense.category = data["category"]
        expense.expense_date = date.fromisoformat(data["expense_date"])
        expense.description = data["description"]
        expense.establishment = data.get("establishment") or None
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
