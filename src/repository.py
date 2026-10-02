from datetime import date
from decimal import Decimal
from sqlalchemy import select
from src.database import SessionLocal
from src.models import Expense

def add_expense(data: dict, raw_text: str | None = None) -> Expense:
    expense = Expense(amount=Decimal(str(data["amount"])), category=data["category"], expense_date=date.fromisoformat(data["expense_date"]), description=data["description"], establishment=data.get("establishment"), raw_text=raw_text)
    with SessionLocal() as session:
        try:
            session.add(expense); session.commit(); session.refresh(expense); return expense
        except Exception:
            session.rollback(); raise

def list_expenses() -> list[Expense]:
    with SessionLocal() as session:
        stmt = select(Expense).order_by(Expense.expense_date.desc(), Expense.id.desc())
        return list(session.scalars(stmt).all())

def delete_expense(expense_id: int) -> bool:
    with SessionLocal() as session:
        expense = session.get(Expense, expense_id)
        if expense is None: return False
        session.delete(expense); session.commit(); return True
