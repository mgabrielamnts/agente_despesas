from datetime import date
from anthropic import Anthropic

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CATEGORIES


TOOL = {
    "name": "analisar_despesa",
    "description": (
        "Analisa uma despesa informada em conversa. Extraia somente informações "
        "que o usuário realmente informou ou que possam ser resolvidas de forma "
        "segura, como hoje e ontem. Use null quando uma informação estiver faltando."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "amount": {"type": ["number", "null"], "exclusiveMinimum": 0},
            "category": {"type": ["string", "null"], "enum": CATEGORIES + [None]},
            "expense_date": {
                "type": ["string", "null"],
                "description": "Data no formato YYYY-MM-DD ou null.",
            },
            "description": {
                "type": ["string", "null"],
                "description": "O que foi comprado ou tipo do gasto.",
            },
            "establishment": {
                "type": ["string", "null"],
                "description": "Estabelecimento apenas quando informado.",
            },
        },
        "required": [
            "amount",
            "category",
            "expense_date",
            "description",
            "establishment",
        ],
        "additionalProperties": False,
    },
}


class ExtractionError(ValueError):
    pass


def _validate_partial(data: dict) -> dict:
    result = {
        "amount": data.get("amount"),
        "category": data.get("category"),
        "expense_date": data.get("expense_date"),
        "description": data.get("description"),
        "establishment": data.get("establishment"),
    }

    if result["amount"] is not None:
        try:
            result["amount"] = round(float(result["amount"]), 2)
        except (TypeError, ValueError) as exc:
            raise ExtractionError("O valor retornado pela IA é inválido.") from exc
        if result["amount"] <= 0:
            raise ExtractionError("O valor da despesa deve ser maior que zero.")

    if result["category"] is not None and result["category"] not in CATEGORIES:
        raise ExtractionError("A categoria retornada não é válida.")

    if result["expense_date"] is not None:
        try:
            result["expense_date"] = date.fromisoformat(result["expense_date"]).isoformat()
        except (TypeError, ValueError) as exc:
            raise ExtractionError("A data retornada pela IA é inválida.") from exc

    if result["description"] is not None:
        result["description"] = str(result["description"]).strip() or None

    if result["establishment"] is not None:
        result["establishment"] = str(result["establishment"]).strip() or None

    return result


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

    if not ANTHROPIC_API_KEY:
        raise ExtractionError("ANTHROPIC_API_KEY não configurada.")

    if not ANTHROPIC_MODEL:
        raise ExtractionError("ANTHROPIC_MODEL não configurado.")

    today = reference_date or date.today()
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    context = previous_data or {}
    prompt = (
        f"Dados já coletados: {context}\n"
        f"Nova mensagem do usuário: {text}\n"
        "Atualize a despesa com base na nova mensagem. "
        "Preserve o sentido do que já foi informado e não invente dados."
    )

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=500,
        system=(
            "Você ajuda a estruturar UMA despesa pessoal por vez em português do Brasil. "
            f"A data de referência é {today.isoformat()}. "
            "Resolva expressões explícitas como hoje e ontem usando essa data. "
            "Não presuma valor, descrição, data ou estabelecimento quando não forem informados. "
            "A categoria pode ser inferida a partir da descrição (ex.: almoço -> Alimentação). "
            "Estabelecimento é opcional. "
            "Use obrigatoriamente a ferramenta analisar_despesa."
        ),
        messages=[{"role": "user", "content": prompt}],
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "analisar_despesa"},
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "analisar_despesa":
            current = _validate_partial(block.input)
            return merge_expense_data(previous_data, current)

    raise ExtractionError("Não consegui interpretar a despesa. Tente novamente.")
