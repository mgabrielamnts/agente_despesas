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
from src.insights import (
    annual_insights,
    detect_anomalies,
    expenses_to_dataframe,
    filter_expenses,
    filter_expenses_by_year,
    monthly_insights,
)
from src.repository import (
    add_expense,
    delete_expense,
    list_expenses,
    mark_anomaly_reviewed,
    migrate_category_labels,
    reviewed_anomaly_ids,
    update_expense,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Agente de Despesas", page_icon="💰", layout="wide")
init_db()
migrate_category_labels()

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

if "anomaly_alert_id" not in st.session_state:
    st.session_state.anomaly_alert_id = None

if "anomaly_edit_id" not in st.session_state:
    st.session_state.anomaly_edit_id = None


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def reset_conversation() -> None:
    st.session_state.expense_draft = {}
    st.session_state.raw_messages = []


def br_date(value) -> str:
    return value.strftime("%d/%m/%Y")


def render_expense_form(
    form_key: str,
    amount: float,
    category: str,
    expense_date: date,
    description: str,
    establishment: str | None,
    submit_label: str,
) -> dict | None:
    with st.form(form_key):
        c1, c2 = st.columns(2)
        edited_amount = c1.number_input(
            "Valor (R$)",
            min_value=0.01,
            value=float(amount),
            step=0.01,
            key=f"{form_key}_amount",
        )
        safe_category = category if category in CATEGORIES else "Outros"
        edited_category = c2.selectbox(
            "Categoria",
            CATEGORIES,
            index=CATEGORIES.index(safe_category),
            key=f"{form_key}_category",
        )
        edited_date = c1.date_input(
            "Data",
            value=expense_date,
            key=f"{form_key}_date",
        )
        edited_description = c2.text_input(
            "Descrição",
            value=description,
            max_chars=200,
            key=f"{form_key}_description",
        )
        edited_establishment = st.text_input(
            "Estabelecimento",
            value=establishment or "",
            max_chars=120,
            key=f"{form_key}_establishment",
        )
        submitted = st.form_submit_button(submit_label, type="primary")

    if not submitted:
        return None

    return {
        "amount": edited_amount,
        "category": edited_category,
        "expense_date": edited_date.isoformat(),
        "description": edited_description.strip(),
        "establishment": edited_establishment.strip() or None,
    }


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
                st.write(f"📅 {br_date(date.fromisoformat(draft['expense_date']))}")
                if draft.get("establishment"):
                    st.write(f"📍 {draft['establishment']}")

                confirm, edit, cancel = st.columns(3)
                if confirm.button("Confirmar e salvar", type="primary", use_container_width=True):
                    draft["category"] = draft.get("category") or "Outros"
                    saved_expense = add_expense(
                        draft,
                        raw_text=" | ".join(st.session_state.raw_messages),
                    )
                    current_df = expenses_to_dataframe(list_expenses())
                    current_anomalies = detect_anomalies(current_df)
                    is_anomaly = (
                        not current_anomalies.empty
                        and "id" in current_anomalies.columns
                        and saved_expense.id in current_anomalies["id"].astype(int).tolist()
                    )

                    if is_anomaly:
                        st.session_state.anomaly_alert_id = saved_expense.id
                        st.session_state.chat_messages.append(
                            {
                                "role": "assistant",
                                "content": "Despesa salva, mas detectei um gasto fora do seu padrão. ⚠️",
                            }
                        )
                    else:
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
        edited_draft = render_expense_form(
            form_key="edit_draft_form",
            amount=float(draft["amount"]),
            category=draft.get("category") or "Outros",
            expense_date=date.fromisoformat(draft["expense_date"]),
            description=draft["description"],
            establishment=draft.get("establishment"),
            submit_label="Salvar edição",
        )

        if edited_draft:
            st.session_state.expense_draft = edited_draft
            st.session_state.edit_draft = False
            st.rerun()

    if st.session_state.anomaly_alert_id is not None:
        alert_expenses = list_expenses()
        alert_expense = next(
            (
                expense
                for expense in alert_expenses
                if expense.id == st.session_state.anomaly_alert_id
            ),
            None,
        )

        if alert_expense is None:
            st.session_state.anomaly_alert_id = None
            st.session_state.anomaly_edit_id = None
        else:
            alert_df = expenses_to_dataframe(alert_expenses)
            alert_anomalies = detect_anomalies(alert_df)
            alert_row = (
                alert_anomalies[
                    alert_anomalies["id"].astype(int) == alert_expense.id
                ]
                if not alert_anomalies.empty and "id" in alert_anomalies.columns
                else alert_anomalies
            )

            with st.chat_message("assistant"):
                st.warning(
                    f"**Gasto fora do seu padrão**\n\n"
                    f"Detectei um valor atípico em **{alert_expense.category}: "
                    f"{money(float(alert_expense.amount))}**. "
                    "O lançamento está correto?"
                )
                keep_col, correct_col, delete_col = st.columns(3)

                if keep_col.button(
                    "✓ Sim, manter",
                    key=f"keep_anomaly_{alert_expense.id}",
                    use_container_width=True,
                ):
                    mark_anomaly_reviewed(alert_expense.id, "confirmed")
                    st.session_state.anomaly_alert_id = None
                    st.session_state.anomaly_edit_id = None
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": "Certo, mantive o lançamento. ✅"}
                    )
                    st.rerun()

                if correct_col.button(
                    "✏️ Corrigir",
                    key=f"correct_anomaly_{alert_expense.id}",
                    use_container_width=True,
                ):
                    st.session_state.anomaly_edit_id = alert_expense.id
                    st.rerun()

                if delete_col.button(
                    "🗑️ Excluir",
                    key=f"delete_anomaly_{alert_expense.id}",
                    use_container_width=True,
                ):
                    delete_expense(alert_expense.id)
                    st.session_state.anomaly_alert_id = None
                    st.session_state.anomaly_edit_id = None
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": "Lançamento excluído. 🗑️"}
                    )
                    st.rerun()

            if st.session_state.anomaly_edit_id == alert_expense.id:
                st.subheader("Corrigir lançamento")
                corrected_data = render_expense_form(
                    form_key=f"anomaly_edit_form_{alert_expense.id}",
                    amount=float(alert_expense.amount),
                    category=alert_expense.category,
                    expense_date=alert_expense.expense_date,
                    description=alert_expense.description,
                    establishment=alert_expense.establishment,
                    submit_label="Salvar correção",
                )
                if corrected_data:
                    update_expense(alert_expense.id, corrected_data)
                    mark_anomaly_reviewed(alert_expense.id, "corrected")
                    st.session_state.anomaly_alert_id = None
                    st.session_state.anomaly_edit_id = None
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": "Lançamento corrigido com sucesso. ✅"}
                    )
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
    view_mode = st.radio(
        "Período",
        ["Mensal", "Anual"],
        horizontal=True,
    )

    if view_mode == "Mensal":
        f1, f2, f3 = st.columns(3)
        year = int(f1.number_input("Ano", 2020, 2100, today.year))
        month = int(f2.selectbox("Mês", range(1, 13), index=today.month - 1))
        category_option = f3.selectbox("Categoria", ["Todas"] + CATEGORIES)
        selected_category = None if category_option == "Todas" else category_option
        info = monthly_insights(df, year, month, selected_category)
        statement = filter_expenses(df, year, month, selected_category)
        previous_label = "Mês anterior"
    else:
        f1, f2 = st.columns(2)
        year = int(f1.number_input("Ano", 2020, 2100, today.year, key="annual_year"))
        category_option = f2.selectbox("Categoria", ["Todas"] + CATEGORIES, key="annual_category")
        selected_category = None if category_option == "Todas" else category_option
        info = annual_insights(df, year, selected_category)
        statement = filter_expenses_by_year(df, year, selected_category)
        previous_label = "Ano anterior"

    m1, m2, m3 = st.columns(3)
    delta = None if info["variation_pct"] is None else f"{info['variation_pct']:+.1f}%"
    m1.metric("Total do período", money(info["total"]), delta=delta)
    m2.metric(previous_label, money(info["previous_total"]))
    m3.metric(
        "Categoria selecionada" if selected_category else "Maior categoria",
        selected_category or info["top_category"] or "Sem dados",
    )

    if view_mode == "Anual":
        st.subheader("Gastos por mês")
        monthly_chart = info["by_month"].rename(
            index={1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                   7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
        )
        st.bar_chart(monthly_chart)

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
        detail["data"] = detail["data"].dt.strftime("%d/%m/%Y")
        detail["descricao"] = detail["descricao"].str.strip().str.capitalize()
        detail["estabelecimento"] = detail["estabelecimento"].fillna("—")
        detail = detail.rename(columns={
            "data": "Data",
            "categoria": "Categoria",
            "descricao": "Descrição",
            "estabelecimento": "Estabelecimento",
            "valor": "Valor (R$)",
        })
        st.dataframe(
            detail,
            use_container_width=True,
            hide_index=True,
            column_config={"Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
        )

    st.subheader("⚠️ Gastos fora do padrão")
    all_anomalies = detect_anomalies(df)
    if view_mode == "Mensal" and not all_anomalies.empty:
        period_anomalies = filter_expenses(
            all_anomalies, year, month, selected_category
        )
    elif view_mode == "Anual" and not all_anomalies.empty:
        period_anomalies = filter_expenses_by_year(
            all_anomalies, year, selected_category
        )
    else:
        period_anomalies = all_anomalies

    reviewed_ids = reviewed_anomaly_ids()
    if not period_anomalies.empty and "id" in period_anomalies.columns:
        period_anomalies = period_anomalies[
            ~period_anomalies["id"].astype(int).isin(reviewed_ids)
        ]

    if period_anomalies.empty:
        st.info("Nenhuma anomalia pendente para este período.")
    else:
        expense_map = {expense.id: expense for expense in expenses}
        for _, anomaly in period_anomalies.iterrows():
            anomaly_id = int(anomaly["id"])
            expense = expense_map.get(anomaly_id)
            if expense is None:
                continue
            difference = float(anomaly["valor"]) - float(anomaly["limite_anomalia"])
            st.warning(
                f"**{br_date(expense.expense_date)} · {expense.category}**  \n"
                f"{expense.description.capitalize()} — **{money(float(expense.amount))}**  \n"
                f"Esse valor ficou **{money(difference)} acima do limite esperado** "
                "para o seu histórico nessa categoria."
            )
            keep, correct, remove = st.columns(3)
            if keep.button("✓ Manter", key=f"dash_keep_{anomaly_id}", use_container_width=True):
                mark_anomaly_reviewed(anomaly_id, "confirmed")
                st.rerun()
            if correct.button("✏️ Corrigir", key=f"dash_correct_{anomaly_id}", use_container_width=True):
                st.session_state.dashboard_anomaly_edit_id = anomaly_id
                st.rerun()
            if remove.button("🗑️ Excluir", key=f"dash_delete_{anomaly_id}", use_container_width=True):
                delete_expense(anomaly_id)
                st.rerun()

            if st.session_state.get("dashboard_anomaly_edit_id") == anomaly_id:
                corrected = render_expense_form(
                    form_key=f"dashboard_anomaly_form_{anomaly_id}",
                    amount=float(expense.amount),
                    category=expense.category,
                    expense_date=expense.expense_date,
                    description=expense.description,
                    establishment=expense.establishment,
                    submit_label="Salvar correção",
                )
                if corrected:
                    update_expense(anomaly_id, corrected)
                    mark_anomaly_reviewed(anomaly_id, "corrected")
                    st.session_state.pop("dashboard_anomaly_edit_id", None)
                    st.rerun()

with tab_history:
    if df.empty:
        st.info("Nenhuma despesa registrada.")
    else:
        display = df.sort_values("data", ascending=False).copy()
        display["data"] = display["data"].dt.strftime("%d/%m/%Y")
        display["descricao"] = display["descricao"].str.strip().str.capitalize()
        display["estabelecimento"] = display["estabelecimento"].fillna("—")
        st.dataframe(display, use_container_width=True, hide_index=True)

        ids = [expense.id for expense in expenses]
        selected_id = st.selectbox(
            "Selecione uma despesa",
            [None] + ids,
            format_func=lambda value: "Selecionar..." if value is None else f"Despesa #{value}",
        )

        if selected_id is not None:
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
                history_data = render_expense_form(
                    form_key="history_edit_form",
                    amount=float(selected.amount),
                    category=selected.category,
                    expense_date=selected.expense_date,
                    description=selected.description,
                    establishment=selected.establishment,
                    submit_label="Salvar alterações",
                )
                if history_data:
                    update_expense(selected_id, history_data)
                    st.session_state.pop("history_edit_id", None)
                    st.success("Despesa atualizada.")
                    st.rerun()
