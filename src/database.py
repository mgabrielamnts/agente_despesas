from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from src.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def init_db() -> None:
    from src import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
