from datetime import date
from anthropic import Anthropic
from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CATEGORIES

TOOL={"name":"registrar_despesa","description":"Extrai uma única despesa pessoal do texto do usuário.","input_schema":{"type":"object","properties":{"amount":{"type":"number","exclusiveMinimum":0},"category":{"type":"string","enum":CATEGORIES},"expense_date":{"type":"string","description":"Data no formato YYYY-MM-DD."},"description":{"type":"string","description":"Descrição curta do gasto."},"establishment":{"type":["string","null"],"description":"Estabelecimento, quando informado."}},"required":["amount","category","expense_date","description","establishment"],"additionalProperties":False}}

class ExtractionError(ValueError): pass

def _validate(data: dict) -> dict:
    required={"amount","category","expense_date","description","establishment"}
    if not required.issubset(data): raise ExtractionError("A IA não retornou todos os campos obrigatórios.")
    try:
        amount=float(data["amount"]); parsed_date=date.fromisoformat(data["expense_date"])
    except (TypeError,ValueError) as exc: raise ExtractionError("Valor ou data retornados pela IA são inválidos.") from exc
    if amount<=0: raise ExtractionError("O valor da despesa deve ser maior que zero.")
    if data["category"] not in CATEGORIES: raise ExtractionError("A categoria retornada não é válida.")
    if not str(data["description"]).strip(): raise ExtractionError("A descrição não pode ficar vazia.")
    return {**data,"amount":round(amount,2),"expense_date":parsed_date.isoformat()}

def extract_expense(text: str, reference_date: date | None = None) -> dict:
    if not text.strip(): raise ExtractionError("Digite uma descrição do gasto.")
    if not ANTHROPIC_API_KEY: raise ExtractionError("ANTHROPIC_API_KEY não configurada.")
    if not ANTHROPIC_MODEL: raise ExtractionError("ANTHROPIC_MODEL não configurado.")
    today=reference_date or date.today(); client=Anthropic(api_key=ANTHROPIC_API_KEY)
    response=client.messages.create(model=ANTHROPIC_MODEL,max_tokens=500,system=("Você extrai despesas pessoais em português do Brasil. "+f"A data de referência é {today.isoformat()}. Resolva hoje/ontem usando essa data. "+"Não invente estabelecimento. Escolha a categoria mais adequada entre as permitidas. Use obrigatoriamente a ferramenta registrar_despesa."),messages=[{"role":"user","content":text}],tools=[TOOL],tool_choice={"type":"tool","name":"registrar_despesa"})
    for block in response.content:
        if getattr(block,"type",None)=="tool_use" and block.name=="registrar_despesa": return _validate(block.input)
    raise ExtractionError("Não foi possível extrair a despesa. Tente escrever de forma mais clara.")
