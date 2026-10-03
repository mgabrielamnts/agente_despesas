from datetime import date
import logging

import streamlit as st

from src.config import CATEGORIES
from src.database import init_db
from src.extraction import (
    ExtractionError,
    extract_expense_turn,
    missing_fields,
    question_for_missing,
)
from src.insights import detect_anomalies, expenses_to_dataframe, filter_expenses, monthly_insights
from src.repository import add_expense, delete_expense, list_expenses, update_expense


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    draft = st.session_state.expense_draft

    chat_area = st.container(height=520)
    with chat_area:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if draft and not missing_fields(draft):
            with st.chat_message("assistant"):
                st.markdown("**Encontrei esta despesa:**")
                st.write(f"💵 {money(draft['amount'])}")
                st.write(f"🏷️ {draft.get('category') or 'Outros'}")
                st.write(f"📝 {draft['description']}")
                st.write(f"📅 {draft['expense_date']}")
                if draft.get("establishment"):
                    st.write(f"📍 {draft['establishment']}")

                confirm, edit, cancel = st.columns(3)
                if confirm.button("Confirmar e salvar", type="primary", use_container_width=True):
                    draft["category"] = draft.get("category") or "Outros"
                    add_expense(draft, raw_text=" | ".join(st.session_state.raw_messages))
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": "Despesa salva com sucesso. ✅ Pode me contar a próxima."}
                    )
                    reset_conversation()
                    st.rerun()

                if edit.button("✏️ Editar", use_container_width=True):
                    st.session_state.edit_draft = True
                    st.rerun()

                if cancel.button("Cancelar", use_container_width=True):
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": "Tudo bem, descartei essa despesa. Pode me contar outra."}
                    )
                    reset_conversation()
                    st.rerun()

    if st.session_state.get("edit_draft") and draft and not missing_fields(draft):
        st.subheader("Editar antes de salvar")
        with st.form("edit_draft_form"):
            e1, e2 = st.columns(2)
            edited_amount = e1.number_input("Valor (R$)", min_value=0.01, value=float(draft["amount"]), step=0.01)
            current_category = draft.get("category") or "Outros"
            edited_category = e2.selectbox("Categoria", CATEGORIES, index=CATEGORIES.index(current_category))
            edited_date = e1.date_input("Data", value=date.fromisoformat(draft["expense_date"]))
            edited_description = e2.text_input("Descrição", value=draft["description"], max_chars=200)
            edited_establishment = st.text_input("Estabelecimento", value=draft.get("establishment") or "", max_chars=120)
            save_edit = st.form_submit_button("Salvar edição", type="primary")

        if save_edit:
            st.session_state.expense_draft = {
                "amount": edited_amount,
                "category": edited_category,
                "expense_date": edited_date.isoformat(),
                "description": edited_description.strip(),
                "establishment": edited_establishment.strip() or None,
            }
            st.session_state.edit_draft = False
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
            reply = question_for_missing(missing) if missing else "Entendi. Confira os dados abaixo antes de eu salvar."
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            st.rerun()

        except ExtractionError as exc:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": f"Não consegui continuar: {exc}"}
            )
            st.rerun()
        except Exception:
            logger.exception("Erro inesperado ao consultar o Gemini")
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": "Não consegui consultar a IA agora. Tente novamente em alguns instantes.",
                }
            )
            st.rerun()


expenses = list_expenses()
df = expenses_to_dataframe(expenses)

with tab_dashboard:
    today = date.today()
    f1, f2, f3 = st.columns(3)
    year = f1.number_input("Ano", 2020, 2100, today.year)
    month = f2.selectbox("Mês", range(1, 13), index=today.month - 1)
    category_option = f3.selectbox("Categoria", ["Todas"] + CATEGORIES)
    selected_category = None if category_option == "Todas" else category_option

    info = monthly_insights(df, int(year), int(month), selected_category)
    statement = filter_expenses(df, int(year), int(month), selected_category)

    m1, m2, m3 = st.columns(3)
    delta = None if info["variation_pct"] is None else f"{info['variation_pct']:+.1f}%"
    m1.metric("Total do período", money(info["total"]), delta=delta)
    m2.metric("Período anterior", money(info["previous_total"]))
    m3.metric(
        "Categoria",
        selected_category or info["top_category"] or "Sem dados",
    )

    if not info["by_category"].empty:
        st.subheader("Gastos por categoria")
        st.bar_chart(info["by_category"])

    st.subheader("Extrato detalhado")
    if statement.empty:
        st.info("Nenhuma despesa encontrada para os filtros selecionados.")
    else:
        detail = statement[
            ["data", "categoria", "descricao", "estabelecimento", "valor"]
        ].copy()
        detail["data"] = detail["data"].dt.date
        detail["estabelecimento"] = detail["estabelecimento"].fillna("—")
        detail = detail.rename(
            columns={
                "data": "Data",
                "categoria": "Categoria",
                "descricao": "Descrição",
                "estabelecimento": "Estabelecimento",
                "valor": "Valor (R$)",
            }
        )
        st.dataframe(
            detail,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )

        category_summary = (
            statement.groupby("categoria")["valor"]
            .agg(["sum", "count"])
            .sort_values("sum", ascending=False)
            .reset_index()
        )
        category_summary.columns = ["Categoria", "Total (R$)", "Lançamentos"]

        with st.expander("Resumo do extrato"):
            st.dataframe(
                category_summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Total (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                },
            )

    st.subheader("Alertas de anomalia")
    anomaly_source = statement if selected_category else filter_expenses(
        df, int(year), int(month)
    )
    anomalies = detect_anomalies(anomaly_source)
    if anomalies.empty:
        st.info("Nenhuma anomalia detectada com o histórico disponível para este filtro.")
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
        display["estabelecimento"] = display["estabelecimento"].fillna("—")
        st.dataframe(display, use_container_width=True, hide_index=True)

        ids = [expense.id for expense in expenses]
        selected_id = st.selectbox("Selecione uma despesa", ids)
        selected = next(expense for expense in expenses if expense.id == selected_id)

        action_edit, action_delete = st.columns(2)

        if action_edit.button("✏️ Editar despesa", use_container_width=True):
            st.session_state.history_edit_id = selected_id

        if action_delete.button("🗑️ Excluir despesa", use_container_width=True):
            delete_expense(selected_id)
            st.success("Despesa excluída.")
            st.rerun()

        if st.session_state.get("history_edit_id") == selected_id:
            st.subheader("Editar despesa")
            with st.form("history_edit_form"):
                h1, h2 = st.columns(2)
                history_amount = h1.number_input(
                    "Valor (R$)",
                    min_value=0.01,
                    value=float(selected.amount),
                    step=0.01,
                    key="history_amount",
                )
                history_category = h2.selectbox(
                    "Categoria",
                    CATEGORIES,
                    index=CATEGORIES.index(selected.category) if selected.category in CATEGORIES else CATEGORIES.index("Outros"),
                    key="history_category",
                )
                history_date = h1.date_input("Data", value=selected.expense_date, key="history_date")
                history_description = h2.text_input("Descrição", value=selected.description, max_chars=200, key="history_description")
                history_establishment = st.text_input(
                    "Estabelecimento",
                    value=selected.establishment or "",
                    max_chars=120,
                    key="history_establishment",
                )
                save_history = st.form_submit_button("Salvar alterações", type="primary")

            if save_history:
                update_expense(
                    selected_id,
                    {
                        "amount": history_amount,
                        "category": history_category,
                        "expense_date": history_date.isoformat(),
                        "description": history_description.strip(),
                        "establishment": history_establishment.strip() or None,
                    },
                )
                st.session_state.pop("history_edit_id", None)
                st.success("Despesa atualizada.")
                st.rerun()
