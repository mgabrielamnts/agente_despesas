# Agente de IA para Análise de Despesas

Projeto de portfólio em Python que transforma descrições de gastos em linguagem natural em dados estruturados, persiste as despesas em banco relacional e gera análises mensais e alertas de anomalias.

## Funcionalidades

- Entrada de despesas em português, como `gastei 45 reais no mercado ontem`.
- Extração estruturada com Claude e **tool use (function calling)**.
- Validação em Python e confirmação manual antes de persistir.
- SQLAlchemy + SQLite, com `DATABASE_URL` preparada para evolução do banco.
- Dashboard mensal com total, comparação com mês anterior e categorias.
- Detecção estatística de gastos atípicos usando IQR.
- Histórico, exclusão de despesas e testes unitários.

## Arquitetura

```text
Usuário -> Streamlit -> Claude/tool use -> validação -> repository -> SQLAlchemy -> SQLite
                                      |
                                      +-> Pandas -> insights/anomalias -> Streamlit
```

## Estrutura

```text
agente_despesas/
├── src/
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── extraction.py
│   ├── repository.py
│   └── insights.py
├── tests/
├── data/
├── app.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Decisões técnicas

A aplicação separa interface, IA, persistência e analytics para reduzir acoplamento. A saída da IA é validada antes da gravação e o usuário pode revisar os campos. O texto original é mantido em `raw_text` para rastreabilidade.

Para anomalias, foi escolhido IQR: dentro de cada categoria com histórico suficiente, gastos acima de `Q3 + 1,5 × IQR` são sinalizados. A abordagem é simples, estatística e explicável, sem adicionar Machine Learning sem necessidade.

## Como executar

Requer Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Preencha no `.env`:

```env
ANTHROPIC_API_KEY=sua_chave_real
ANTHROPIC_MODEL=nome_do_modelo_disponivel_na_sua_conta
```

Execute:

```bash
streamlit run app.py
```

O banco `data/expenses.db` é criado automaticamente e não é versionado.

## Testes

```bash
pytest
```

## Exemplo

Entrada: `almoço 32,50 hoje no ifood`.

Saída estruturada esperada:

```json
{"amount":32.50,"category":"Alimentação","expense_date":"2026-10-01","description":"Almoço","establishment":"iFood"}
```

## Stack

Python · Anthropic SDK · SQLAlchemy · SQLite · Pandas · Streamlit · Pytest

## Próximas evoluções

PostgreSQL/Alembic, metas por categoria, exportação CSV, filtros adicionais e mocks da API nos testes.
