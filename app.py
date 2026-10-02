from datetime import date

import streamlit as st

from src.database import init_db
from src.extraction import (
    ExtractionError,
    extract_expense_turn,
    missing_fields,
    question_for_missing,
)
from src.insights import detect_anomalies, expenses_to_dataframe, monthly_insights
from src.repository import add_expense, delete_expense, list_expenses


st.set_page_config(page_title="Agente de Despesas", page_icon="💰", layout="wide")
init_db()

st.title("💰 Agente de IA para Análise de Despesas")
st.caption("Converse com o agente para registrar seus gastos e acompanhar seus padrões.")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "Oi! Me conte uma despesa que você teve."}
    ]

if "expense_draft" not in st.session_state:
    st.session_state.expense_draft = {}

if "raw_messages" not in st.session_state:
    st.session_state.raw_messages = []


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def reset_conversation() -> None:
    st.session_state.expense_draft = {}
    st.session_state.raw_messages = []


tab_chat, tab_dashboard, tab_history = st.tabs(["💬 Conversa", "📊 Dashboard", "📋 Histórico"])

with tab_chat:
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    draft = st.session_state.expense_draft
    if draft and not missing_fields(draft):
        with st.chat_message("assistant"):
            st.markdown("**Encontrei esta despesa:**")
            st.write(f"💵 {money(draft['amount'])}")
            st.write(f"🏷️ {draft.get('category') or 'Outros'}")
            st.write(f"📝 {draft['description']}")
            st.write(f"📅 {draft['expense_date']}")
            if draft.get("establishment"):
                st.write(f"📍 {draft['establishment']}")

            confirm, cancel = st.columns(2)
            if confirm.button("Confirmar e salvar", type="primary", use_container_width=True):
                draft["category"] = draft.get("category") or "Outros"
                add_expense(
                    draft,
                    raw_text=" | ".join(st.session_state.raw_messages),
                )
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": "Despesa salva com sucesso. ✅ Pode me contar a próxima."}
                )
                reset_conversation()
                st.rerun()

            if cancel.button("Cancelar", use_container_width=True):
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": "Tudo bem, descartei essa despesa. Pode me contar outra."}
                )
                reset_conversation()
                st.rerun()

    user_text = st.chat_input("Ex.: gastei 45 reais no mercado ontem")

    if user_text:
        st.session_state.chat_messages.append({"role": "user", "content": user_text})
        st.session_state.raw_messages.append(user_text)

        try:
            updated = extract_expense_turn(
                user_text,
                previous_data=st.session_state.expense_draft,
            )
            st.session_state.expense_draft = updated
            missing = missing_fields(updated)

            if missing:
                reply = question_for_missing(missing)
            else:
                reply = "Entendi. Confira os dados abaixo antes de eu salvar."

            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            st.rerun()

        except ExtractionError as exc:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": f"Não consegui continuar: {exc}"}
            )
            st.rerun()
        except Exception as exc:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": f"Falha ao consultar a IA: {exc}"}
            )
            st.rerun()


expenses = list_expenses()
df = expenses_to_dataframe(expenses)

with tab_dashboard:
    today = date.today()
    c1, c2 = st.columns(2)
    year = c1.number_input("Ano", 2020, 2100, today.year)
    month = c2.selectbox("Mês", range(1, 13), index=today.month - 1)

    info = monthly_insights(df, int(year), int(month))
    m1, m2, m3 = st.columns(3)

    delta = None if info["variation_pct"] is None else f"{info['variation_pct']:+.1f}%"
    m1.metric("Total do mês", money(info["total"]), delta=delta)
    m2.metric("Mês anterior", money(info["previous_total"]))
    m3.metric("Maior categoria", info["top_category"] or "Sem dados")

    if not info["by_category"].empty:
        st.subheader("Gastos por categoria")
        st.bar_chart(info["by_category"])

    st.subheader("Alertas de anomalia")
    anomalies = detect_anomalies(df)
    if anomalies.empty:
        st.info("Nenhuma anomalia detectada com o histórico disponível.")
    else:
        st.dataframe(
            anomalies[["data", "categoria", "descricao", "valor", "limite_anomalia"]],
            use_container_width=True,
        )

with tab_history:
    if df.empty:
        st.info("Nenhuma despesa registrada.")
    else:
        display = df.sort_values("data", ascending=False).copy()
        display["data"] = display["data"].dt.date
        st.dataframe(display, use_container_width=True, hide_index=True)

        ids = [expense.id for expense in expenses]
        selected_id = st.selectbox("ID para excluir", ids)
        if st.button("Excluir despesa"):
            delete_expense(selected_id)
            st.success("Despesa excluída.")
            st.rerun()
