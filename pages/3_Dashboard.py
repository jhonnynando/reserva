from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from services.reserva_service import available_years, distinct_values, list_reservas
from utils.formatacao import format_currency_br
from utils.ui import bootstrap_database, metric_card, page_header, render_sidebar, setup_page
from utils.validacao import clean_text


MONTHS = [
    ("Todos", None),
    ("Janeiro", 1),
    ("Fevereiro", 2),
    ("Março", 3),
    ("Abril", 4),
    ("Maio", 5),
    ("Junho", 6),
    ("Julho", 7),
    ("Agosto", 8),
    ("Setembro", 9),
    ("Outubro", 10),
    ("Novembro", 11),
    ("Dezembro", 12),
]


def _choice(label: str, options: list[str], key: str) -> str | None:
    selected = st.selectbox(label, ["Todos"] + options, key=key)
    return None if selected == "Todos" else selected


def _dashboard_filters() -> dict[str, Any]:
    years = available_years()
    with st.form("dashboard_filtros_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            data_inicio = st.date_input("Data inicial", value=None, format="DD/MM/YYYY", key="d_data_inicio")
        with col2:
            data_fim = st.date_input("Data final", value=None, format="DD/MM/YYYY", key="d_data_fim")
        with col3:
            ano = st.selectbox("Ano", ["Todos"] + years, key="d_ano")
        with col4:
            mes = st.selectbox("M?s", MONTHS, format_func=lambda item: item[0], key="d_mes")

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            cidade = _choice("Cidade", distinct_values("cidade"), "d_cidade")
        with col6:
            motorista = _choice("Motorista", distinct_values("motorista"), "d_motorista")
        with col7:
            categoria = _choice("Categoria", distinct_values("categoria"), "d_categoria")
        with col8:
            aplicar = st.form_submit_button("Aplicar filtros", type="primary", width="stretch")

    filtros = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "ano": None if ano == "Todos" else ano,
        "mes": mes[1],
        "cidade": cidade,
        "motorista": motorista,
        "categoria": categoria,
    }
    if aplicar or "dashboard_filtros_aplicados" not in st.session_state:
        st.session_state["dashboard_filtros_aplicados"] = filtros
    return st.session_state["dashboard_filtros_aplicados"]


def _prepare_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["data_reserva"] = pd.to_datetime(df["data_reserva"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df["dias"] = pd.to_numeric(df["dias"], errors="coerce").fillna(0).astype(int)
    for field in ["cidade", "hotel_pousada", "motorista", "categoria", "tipo"]:
        df[field] = df[field].fillna("").replace("", "Sem informação")
    df["planejamento"] = df["nao_planejada"].map({True: "Não planejada", False: "Planejada"})
    df["mes_ref"] = df["data_reserva"].dt.to_period("M").dt.to_timestamp()
    df["mes_label"] = df["mes_ref"].dt.strftime("%m/%Y")
    return df


def _top_label(df: pd.DataFrame, field: str) -> str:
    if df.empty:
        return "-"
    grouped = df.groupby(field, as_index=False)["valor"].sum().sort_values("valor", ascending=False)
    if grouped.empty:
        return "-"
    first = grouped.iloc[0]
    return f"{first[field]} ({format_currency_br(first['valor'])})"


def _metric_cards(df: pd.DataFrame) -> None:
    if df.empty:
        total = media = percentual_np = 0
        qtd = nao_planejadas = 0
    else:
        total = df["valor"].sum()
        qtd = len(df)
        media = total / qtd if qtd else 0
        nao_planejadas = int(df["nao_planejada"].sum())
        percentual_np = (nao_planejadas / qtd * 100) if qtd else 0

    row1 = st.columns(5)
    metrics = [
        ("Valor total", format_currency_br(total)),
        ("Número de reservas", str(qtd)),
        ("Média por reserva", format_currency_br(media)),
        ("Total não planejado", str(nao_planejadas)),
        ("% não planejado", f"{percentual_np:.1f}%".replace(".", ",")),
    ]
    for col, (label, value) in zip(row1, metrics):
        with col:
            metric_card(label, value, accent="green" if label == "Valor total" else "blue")

    row2 = st.columns(3)
    with row2[0]:
        metric_card("Cidade com maior gasto", _top_label(df, "cidade"))
    with row2[1]:
        metric_card("Hotel com maior gasto", _top_label(df, "hotel_pousada"))
    with row2[2]:
        metric_card("Motorista com maior gasto", _top_label(df, "motorista"))


def _bar_sum(df: pd.DataFrame, field: str, title: str, top: int | None = None):
    grouped = df.groupby(field, as_index=False)["valor"].sum().sort_values("valor", ascending=False)
    if top:
        grouped = grouped.head(top)
    return px.bar(grouped, x=field, y="valor", title=title, text_auto=".2s", color_discrete_sequence=["#145DA0"])


def _bar_count(df: pd.DataFrame, field: str, title: str):
    grouped = df.groupby(field, as_index=False)["id"].count().rename(columns={"id": "reservas"})
    return px.bar(grouped, x=field, y="reservas", title=title, text_auto=True, color_discrete_sequence=["#16A34A"])


def _render_charts(df: pd.DataFrame) -> None:
    monthly = df.groupby(["mes_ref", "mes_label"], as_index=False)["valor"].sum().sort_values("mes_ref")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            monthly,
            x="mes_label",
            y="valor",
            title="Gastos por mês",
            color_discrete_sequence=["#145DA0"],
        )
        st.plotly_chart(fig, width="stretch")
    with col2:
        fig = px.line(
            monthly,
            x="mes_label",
            y="valor",
            markers=True,
            title="Evolução mensal dos gastos",
            color_discrete_sequence=["#16A34A"],
        )
        st.plotly_chart(fig, width="stretch")

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(_bar_sum(df, "cidade", "Gastos por cidade", top=15), width="stretch")
    with col4:
        st.plotly_chart(_bar_sum(df, "hotel_pousada", "Gastos por hotel", top=15), width="stretch")

    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(_bar_sum(df, "motorista", "Gastos por motorista", top=15), width="stretch")
    with col6:
        st.plotly_chart(_bar_sum(df, "categoria", "Gastos por categoria", top=15), width="stretch")

    col7, col8 = st.columns(2)
    with col7:
        planejamento = df.groupby("planejamento", as_index=False)["id"].count().rename(columns={"id": "reservas"})
        fig = px.pie(
            planejamento,
            names="planejamento",
            values="reservas",
            title="Reservas planejadas versus não planejadas",
            color_discrete_sequence=["#145DA0", "#16A34A"],
        )
        st.plotly_chart(fig, width="stretch")
    with col8:
        st.plotly_chart(_bar_count(df, "tipo", "Quantidade de reservas por tipo"), width="stretch")

    col9, col10 = st.columns(2)
    with col9:
        st.plotly_chart(_bar_sum(df, "hotel_pousada", "Top 10 hotéis com maior gasto", top=10), width="stretch")
    with col10:
        st.plotly_chart(_bar_sum(df, "cidade", "Top 10 cidades com maior gasto", top=10), width="stretch")


setup_page("Dashboard")
bootstrap_database()
render_sidebar(None)
page_header("Dashboard", "Indicadores e análises das reservas filtradas.")

filters = _dashboard_filters()
df = _prepare_df(list_reservas(filters))
_metric_cards(df)

if df.empty:
    st.info("Nenhum dado encontrado para os filtros selecionados.")
else:
    _render_charts(df)

