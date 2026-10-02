# Agente de IA para Análise de Despesas

Projeto de portfólio em Python que usa uma interface conversacional para transformar linguagem natural em despesas estruturadas, persistir os dados em banco relacional e gerar análises mensais e alertas de anomalias.

## Funcionalidades

- Chat em português para registrar despesas naturalmente.
- Coleta conversacional: se faltar valor, descrição ou data, o agente pergunta em vez de inventar.
- Categorização automática a partir da descrição.
- Extração estruturada com Claude e **tool use (function calling)**.
- Confirmação humana antes da persistência.
- SQLAlchemy + SQLite, com `DATABASE_URL` preparada para evolução do banco.
- Dashboard mensal com total, comparação com mês anterior e categorias.
- Detecção estatística de gastos atípicos usando IQR.
- Histórico e exclusão de despesas.

## Exemplo de conversa

```text
Usuário: Fui no McDonald's ontem.
Agente: Quanto você gastou?
Usuário: 38,90
Agente: Encontrei esta despesa:
        R$ 38,90 · Alimentação · McDonald's · ontem
        [Confirmar e salvar] [Cancelar]
```

O estabelecimento é opcional. Valor, descrição e data precisam estar definidos antes da gravação.

## Arquitetura

```text
Usuário -> Streamlit Chat -> Claude/tool use -> validação
                                      |
                                      v
                              confirmação humana
                                      |
                                      v
                         repository -> SQLAlchemy -> SQLite
                                      |
                                      v
                           Pandas -> insights/anomalias
```

O modelo não grava diretamente no banco. Ele produz dados estruturados; o código Python valida, pede informações ausentes e somente chama a persistência após confirmação do usuário.

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

## Como executar

Requer Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure no `.env`:

```env
ANTHROPIC_API_KEY=sua_chave_real
ANTHROPIC_MODEL=nome_do_modelo_disponivel_na_sua_conta
```

Execute:

```bash
streamlit run app.py
```

## Testes

```bash
pytest
```

## Stack

Python · Anthropic SDK · SQLAlchemy · SQLite · Pandas · Streamlit · Pytest

## Próximas evoluções

1. Consultas conversacionais sobre os próprios gastos.
2. Insights proativos e comparação entre categorias.
3. Identificação de recorrências e assinaturas.
4. Personalidades desacopladas da regra de negócio.
5. Interface visual temática/pixel art e futura experiência mobile.
