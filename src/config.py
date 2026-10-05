import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'expenses.db'}")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

CATEGORIES = [
    "Alimentação",
    "Mercado",
    "Transporte",
    "Moradia",
    "Contas pessoais",
    "Saúde",
    "Educação",
    "Lazer",
    "Compras",
    "Assinaturas",
    "Financeiro",
    "Outros",
]
