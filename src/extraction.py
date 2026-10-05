from datetime import date

from google import genai

from src.config import CATEGORIES, GEMINI_API_KEY, GEMINI_MODEL
from src.time_utils import local_today
from src.validation import ExpenseValidationError, validate_expense_data

TOOL = {
    "type": "function",
    "name": "analisar_despesa",
    "description": (
        "Estrutura os dados conhecidos de uma única despesa pessoal. "
        "Campos desconhecidos devem ser omitidos."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "amount": {"type": "number", "description": "Valor da despesa, maior que zero."},
            "category": {"type": "string", "enum": CATEGORIES, "description": "Categoria inferida a partir do gasto."},
            "expense_date": {"type": "string", "description": "Data no formato YYYY-MM-DD."},
            "description": {"type": "string", "description": "O que foi comprado ou tipo do gasto."},
            "establishment": {"type": "string", "description": "Estabelecimento somente quando informado."},
        },
    },
}


class ExtractionError(ValueError):
    pass


def _validate_partial(data: dict, reference_date: date | None = None) -> dict:
    try:
        return validate_expense_data(
            data,
            reference_date=reference_date or local_today(),
            partial=True,
        )
    except ExpenseValidationError as exc:
        raise ExtractionError(str(exc)) from exc


def merge_expense_data(previous: dict | None, new: dict) -> dict:
    merged = dict(previous or {})
    for key, value in new.items():
        if value is not None:
            merged[key] = value
        elif key not in merged:
            merged[key] = None
    return merged


def missing_fields(data: dict) -> list[str]:
    required = ["amount", "description", "expense_date"]
    return [field for field in required if not data.get(field)]


def question_for_missing(fields: list[str]) -> str:
    questions = {
        "amount": "Quanto você gastou?",
        "description": "Com o que foi esse gasto?",
        "expense_date": "Em que dia foi esse gasto?",
    }
    return questions[fields[0]] if fields else ""


def extract_expense_turn(
    text: str,
    previous_data: dict | None = None,
    reference_date: date | None = None,
) -> dict:
    if not text.strip():
        raise ExtractionError("Digite uma mensagem.")
    if not GEMINI_API_KEY:
        raise ExtractionError("GEMINI_API_KEY não configurada.")

    today = reference_date or local_today()
    context = previous_data or {}
    prompt = (
        "Você ajuda a estruturar UMA despesa pessoal por vez em português do Brasil.\n"
        f"A data de referência é {today.isoformat()}.\n"
        f"Dados já coletados: {context}\n"
        f"Nova mensagem do usuário: {text}\n\n"
        "Regras:\n"
        "- Atualize a despesa usando a nova mensagem e os dados já coletados.\n"
        "- Não invente valor, descrição, data ou estabelecimento.\n"
        "- Resolva expressões explícitas como hoje e ontem usando a data de referência.\n"
        "- A categoria pode ser inferida pela descrição, por exemplo almoço -> Alimentação.\n"
        "- Estabelecimento é opcional.\n"
        "- Omita da chamada os campos que ainda não são conhecidos.\n"
        "- Chame analisar_despesa com os dados disponíveis."
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        tools=[TOOL],
        store=False,
        generation_config={
            "tool_choice": {
                "allowed_tools": {"mode": "any", "tools": ["analisar_despesa"]}
            }
        },
    )

    for step in interaction.steps:
        if step.type == "function_call" and step.name == "analisar_despesa":
            current = _validate_partial(dict(step.arguments), reference_date=today)
            return merge_expense_data(previous_data, current)

    raise ExtractionError("Não consegui interpretar a despesa. Tente novamente.")
