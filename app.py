from datetime import date
import streamlit as st
from src.config import CATEGORIES
from src.database import init_db
from src.extraction import ExtractionError, extract_expense
from src.insights import detect_anomalies, expenses_to_dataframe, monthly_insights
from src.repository import add_expense, delete_expense, list_expenses

st.set_page_config(page_title="Agente de Despesas",page_icon="💰",layout="wide"); init_db()
st.title("💰 Agente de IA para Análise de Despesas"); st.caption("Registre gastos em linguagem natural e acompanhe seus padrões de consumo.")
tab_new,tab_dashboard,tab_history=st.tabs(["Nova despesa","Dashboard","Histórico"])
with tab_new:
    text=st.text_input("Descreva seu gasto",placeholder="Ex.: gastei 45 reais no mercado ontem")
    if st.button("Analisar despesa",type="primary"):
        try: st.session_state["pending_expense"]=extract_expense(text); st.session_state["raw_text"]=text
        except ExtractionError as exc: st.error(str(exc))
        except Exception as exc: st.error(f"Falha ao consultar a IA: {exc}")
    pending=st.session_state.get("pending_expense")
    if pending:
        st.subheader("Confira antes de salvar"); c1,c2=st.columns(2)
        amount=c1.number_input("Valor (R$)",min_value=.01,value=float(pending["amount"]),step=.01)
        category=c2.selectbox("Categoria",[pending["category"]]+[c for c in CATEGORIES if c!=pending["category"]])
        expense_date=c1.date_input("Data",value=date.fromisoformat(pending["expense_date"])); description=c2.text_input("Descrição",value=pending["description"]); establishment=st.text_input("Estabelecimento",value=pending.get("establishment") or "")
        if st.button("Confirmar e salvar"):
            add_expense({"amount":amount,"category":category,"expense_date":expense_date.isoformat(),"description":description,"establishment":establishment or None},st.session_state.get("raw_text")); st.session_state.pop("pending_expense",None); st.session_state.pop("raw_text",None); st.success("Despesa salva com sucesso."); st.rerun()
expenses=list_expenses(); df=expenses_to_dataframe(expenses)
with tab_dashboard:
    today=date.today(); c1,c2=st.columns(2); year=c1.number_input("Ano",2020,2100,today.year); month=c2.selectbox("Mês",range(1,13),index=today.month-1); info=monthly_insights(df,int(year),int(month)); m1,m2,m3=st.columns(3)
    m1.metric("Total do mês",f"R$ {info['total']:,.2f}"); delta=None if info["variation_pct"] is None else f"{info['variation_pct']:+.1f}%"; m2.metric("Mês anterior",f"R$ {info['previous_total']:,.2f}",delta=delta); m3.metric("Maior categoria",info["top_category"] or "Sem dados")
    if not info["by_category"].empty: st.subheader("Gastos por categoria"); st.bar_chart(info["by_category"])
    st.subheader("Alertas de anomalia"); anomalies=detect_anomalies(df)
    if anomalies.empty: st.info("Nenhuma anomalia detectada com o histórico disponível.")
    else: st.dataframe(anomalies[["data","categoria","descricao","valor","limite_anomalia"]],use_container_width=True)
with tab_history:
    if df.empty: st.info("Nenhuma despesa registrada.")
    else:
        display=df.sort_values("data",ascending=False).copy(); display["data"]=display["data"].dt.date; st.dataframe(display,use_container_width=True,hide_index=True); ids=[e.id for e in expenses]; selected_id=st.selectbox("ID para excluir",ids)
        if st.button("Excluir despesa"): delete_expense(selected_id); st.success("Despesa excluída."); st.rerun()
