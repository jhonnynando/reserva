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
    page_header("Painel inicial", "Sistema aberto para cadastro, consulta e analise de reservas.")
    _home_metrics()

    st.markdown("### Acesso rapido")
    cols = st.columns(3)
    with cols[0]:
        st.page_link("pages/1_Cadastro.py", label="Cadastrar reserva", icon=":material/add_circle:")
    with cols[1]:
        st.page_link("pages/2_Reservas.py", label="Consultar reservas", icon=":material/table_view:")
    with cols[2]:
        st.page_link("pages/3_Dashboard.py", label="Dashboard", icon=":material/monitoring:")


setup_page("Inicio")
bootstrap_database()
render_sidebar(None)
_home()
