from __future__ import annotations

import pandas as pd
import streamlit as st

from services.reserva_service import list_reservas
from utils.formatacao import format_currency_br
from utils.ui import bootstrap_database, metric_card, page_header, render_sidebar, setup_page


def _home_metrics() -> None:
    records = list_reservas({})
    df = pd.DataFrame(records)
    if df.empty:
        total = 0
        quantidade = 0
        nao_planejadas = 0
    else:
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
        total = df["valor"].sum()
        quantidade = len(df)
        nao_planejadas = int(df["nao_planejada"].sum())

    cols = st.columns(3)
    with cols[0]:
        metric_card("Valor total registrado", format_currency_br(total))
    with cols[1]:
        metric_card("Reservas registradas", str(quantidade), accent="green")
    with cols[2]:
        metric_card("Nao planejadas", str(nao_planejadas))


def _home() -> None:
    page_header("Painel inicial", "Acompanhe a operação diária e os indicadores de hospedagem.")
    _home_metrics()

    st.markdown(
        """
        <div class="main-section-heading">
            <span>Acesso principal</span>
            <strong>O que você precisa agora?</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    with cols[0]:
        st.page_link("pages/2_Reservas.py", label="Abrir reservas", icon=":material/event_available:")
    with cols[1]:
        st.page_link("pages/3_Dashboard.py", label="Ver dashboard", icon=":material/monitoring:")

    st.markdown(
        """
        <div class="main-section-heading">
            <span>Outras ações</span>
            <strong>Cadastro e importação</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    support_cols = st.columns(2)
    with support_cols[0]:
        st.page_link("pages/1_Cadastro.py", label="Cadastrar nova reserva", icon=":material/add_circle:")
    with support_cols[1]:
        st.page_link("pages/4_Importar_Excel.py", label="Importar planilha", icon=":material/upload_file:")


setup_page("Inicio")
bootstrap_database()
render_sidebar(None, "Inicio")
_home()
