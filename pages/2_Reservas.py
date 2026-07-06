from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

from services.reserva_service import (
    DuplicateReservationError,
    available_years,
    delete_reserva,
    distinct_values,
    get_reserva,
    list_reservas,
    update_reserva,
)
from utils.formatacao import format_currency_br, format_date_br, parse_decimal_br
from utils.ui import bootstrap_database, metric_card, page_header, render_sidebar, setup_page
from utils.validacao import clean_text, validate_reserva


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


FILTER_KEYS = [
    "f_data_inicio",
    "f_data_fim",
    "f_ano",
    "f_mes",
    "f_dia",
    "f_motorista",
    "f_ajudante",
    "f_cidade",
    "f_hotel",
    "f_tipo",
    "f_categoria",
    "f_nao_planejada",
    "f_valor_min",
    "f_valor_max",
    "f_busca",
]


def _choice(label: str, options: list[str], key: str) -> str | None:
    selected = st.selectbox(label, ["Todos"] + options, key=key)
    return None if selected == "Todos" else selected


def _build_filters() -> dict[str, Any]:
    years = available_years()
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        data_inicio = st.date_input("Período inicial", value=None, format="DD/MM/YYYY", key="f_data_inicio")
    with col2:
        data_fim = st.date_input("Período final", value=None, format="DD/MM/YYYY", key="f_data_fim")
    with col3:
        ano = st.selectbox("Ano", ["Todos"] + years, key="f_ano")
    with col4:
        mes = st.selectbox("Mês", MONTHS, format_func=lambda item: item[0], key="f_mes")
    with col5:
        dia = st.selectbox("Dia", ["Todos"] + list(range(1, 32)), key="f_dia")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        motorista = _choice("Motorista", distinct_values("motorista"), "f_motorista")
    with col6:
        ajudante = _choice("Ajudante", distinct_values("ajudante"), "f_ajudante")
    with col7:
        cidade = _choice("Cidade", distinct_values("cidade"), "f_cidade")
    with col8:
        hotel = _choice("Hotel/Pousada", distinct_values("hotel_pousada"), "f_hotel")

    col9, col10, col11, col12 = st.columns(4)
    with col9:
        tipo = _choice("Tipo", distinct_values("tipo"), "f_tipo")
    with col10:
        categoria = _choice("Categoria", distinct_values("categoria"), "f_categoria")
    with col11:
        nao_planejada_choice = st.selectbox("Não planejada", ["Todas", "Sim", "Não"], key="f_nao_planejada")
    with col12:
        busca = st.text_input("Busca geral", key="f_busca")

    col13, col14, col15 = st.columns([1, 1, 1])
    with col13:
        valor_min = parse_decimal_br(st.text_input("Valor mínimo", key="f_valor_min"))
    with col14:
        valor_max = parse_decimal_br(st.text_input("Valor máximo", key="f_valor_max"))
    with col15:
        st.write("")
        st.write("")
        if st.button("Limpar filtros", width="stretch"):
            for key in FILTER_KEYS:
                st.session_state.pop(key, None)
            st.rerun()

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "ano": None if ano == "Todos" else ano,
        "mes": mes[1],
        "dia": None if dia == "Todos" else dia,
        "motorista": motorista,
        "ajudante": ajudante,
        "cidade": cidade,
        "hotel_pousada": hotel,
        "tipo": tipo,
        "categoria": categoria,
        "nao_planejada": {"Todas": None, "Sim": True, "Não": False}[nao_planejada_choice],
        "valor_min": valor_min,
        "valor_max": valor_max,
        "busca": clean_text(busca),
    }


def _prepare_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["data_reserva"] = pd.to_datetime(df["data_reserva"])
    df["ano"] = df["data_reserva"].dt.year
    df["mes"] = df["data_reserva"].dt.month
    df["dia"] = df["data_reserva"].dt.day
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df["dias"] = pd.to_numeric(df["dias"], errors="coerce").fillna(0).astype(int)
    return df


def _display_metrics(df: pd.DataFrame) -> None:
    if df.empty:
        total = media = media_dia = 0
        qtd = nao_planejadas = dias = 0
    else:
        total = df["valor"].sum()
        qtd = len(df)
        media = total / qtd if qtd else 0
        nao_planejadas = int(df["nao_planejada"].sum())
        dias = int(df["dias"].sum())
        media_dia = total / dias if dias else 0

    cols = st.columns(6)
    values = [
        ("Total geral", format_currency_br(total)),
        ("Registros filtrados", str(qtd)),
        ("Média por reserva", format_currency_br(media)),
        ("Não planejadas", str(nao_planejadas)),
        ("Total de dias", str(dias)),
        ("Média por dia", format_currency_br(media_dia)),
    ]
    for col, (label, value) in zip(cols, values):
        with col:
            metric_card(label, value, accent="green" if label == "Total geral" else "blue")


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    output = pd.DataFrame(
        {
            "ID": df["id"],
            "Data": df["data_reserva"].dt.strftime("%d/%m/%Y"),
            "Motorista": df["motorista"],
            "Ajudante": df["ajudante"],
            "Cidade": df["cidade"],
            "Hotel/Pousada": df["hotel_pousada"],
            "Tipo": df["tipo"],
            "Valor": df["valor"].apply(format_currency_br),
            "Dias": df["dias"],
            "Não planejada": df["nao_planejada"].map({True: "Sim", False: "Não"}),
            "Categoria": df["categoria"],
            "Observação": df["observacao"],
        }
    )
    return output


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reservas")
    return buffer.getvalue()


def _export_buttons(df: pd.DataFrame) -> None:
    formatted = _format_table(df)
    col_csv, col_excel = st.columns(2)
    with col_csv:
        st.download_button(
            "Exportar CSV",
            data=formatted.to_csv(index=False, sep=";", encoding="utf-8-sig"),
            file_name="reservas_filtradas.csv",
            mime="text/csv",
            width="stretch",
        )
    with col_excel:
        st.download_button(
            "Exportar Excel",
            data=_to_excel_bytes(formatted),
            file_name="reservas_filtradas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def _sort_and_paginate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    sort_options = {
        "Data": ["data_reserva"],
        "Ano": ["ano", "mes", "dia", "data_reserva"],
        "Mês": ["mes", "dia", "ano", "data_reserva"],
        "Dia": ["dia", "mes", "ano", "data_reserva"],
        "Ano/Mês/Dia": ["ano", "mes", "dia"],
        "Motorista": ["motorista", "data_reserva"],
        "Ajudante": ["ajudante", "data_reserva"],
        "Cidade": ["cidade", "data_reserva"],
        "Hotel/Pousada": ["hotel_pousada", "data_reserva"],
        "Tipo": ["tipo", "data_reserva"],
        "Valor": ["valor", "data_reserva"],
        "Dias": ["dias", "data_reserva"],
        "Categoria": ["categoria", "data_reserva"],
    }
    col_sort, col_dir, col_size, col_page = st.columns(4)
    with col_sort:
        sort_label = st.selectbox("Ordenar por", list(sort_options.keys()), index=0)
    with col_dir:
        ascending = st.selectbox("Direção", ["Decrescente", "Crescente"]) == "Crescente"
    sorted_df = df.sort_values(sort_options[sort_label], ascending=ascending, na_position="last")
    with col_size:
        page_size = st.selectbox("Registros por página", [10, 25, 50, 100], index=1)
    total_pages = max(1, (len(sorted_df) + page_size - 1) // page_size)
    with col_page:
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)
    start = (int(page) - 1) * page_size
    return sorted_df.iloc[start : start + page_size]


def _reserva_label(df: pd.DataFrame, reserva_id: int) -> str:
    row = df.loc[df["id"] == reserva_id].iloc[0]
    return f"#{reserva_id} - {format_date_br(row['data_reserva'])} - {row['motorista']} - {format_currency_br(row['valor'])}"


def _edit_reserva(df: pd.DataFrame) -> None:
    if df.empty:
        return
    with st.expander("Editar reserva"):
        ids = df["id"].astype(int).tolist()
        reserva_id = st.selectbox(
            "Selecione a reserva",
            ids,
            format_func=lambda item: _reserva_label(df, item),
            key="edit_reserva_id",
        )
        reserva = get_reserva(int(reserva_id))
        if not reserva:
            st.warning("Reserva não encontrada.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            data_reserva = st.date_input("Data", value=reserva["data_reserva"], format="DD/MM/YYYY", key="edit_data")
            motorista = st.text_input("Motorista", value=reserva["motorista"] or "", key="edit_motorista")
            ajudante = st.text_input("Ajudante", value=reserva["ajudante"] or "", key="edit_ajudante")
        with col2:
            cidade = st.text_input("Cidade", value=reserva["cidade"] or "", key="edit_cidade")
            hotel = st.text_input("Hotel/Pousada", value=reserva["hotel_pousada"] or "", key="edit_hotel")
            tipo = st.text_input("Tipo", value=reserva["tipo"] or "", key="edit_tipo")
        with col3:
            valor = st.text_input("Valor", value=format_currency_br(reserva["valor"]), key="edit_valor")
            dias = st.number_input("Dias", min_value=1, value=int(reserva["dias"]), step=1, key="edit_dias")
            nao_planejada = st.checkbox("Não planejada", value=bool(reserva["nao_planejada"]), key="edit_np")
        categoria = st.text_input("Categoria", value=reserva["categoria"] or "", key="edit_categoria")
        observacao = st.text_area("Observação", value=reserva["observacao"] or "", height=90, key="edit_obs")
        allow_duplicate = st.checkbox("Salvar mesmo que exista possível duplicidade", key="edit_allow_dup")

        if st.button("Salvar alterações", type="primary", width="stretch"):
            data = {
                "data_reserva": data_reserva,
                "motorista": motorista,
                "ajudante": ajudante,
                "cidade": cidade,
                "hotel_pousada": hotel,
                "tipo": tipo,
                "valor": parse_decimal_br(valor),
                "dias": int(dias),
                "nao_planejada": nao_planejada,
                "categoria": categoria,
                "observacao": observacao,
            }
            errors = validate_reserva(data)
            if errors:
                for error in errors:
                    st.warning(error)
                return
            try:
                update_reserva(int(reserva_id), data, allow_duplicate=allow_duplicate)
                st.success("Reserva atualizada.")
                st.rerun()
            except DuplicateReservationError as exc:
                st.warning(
                    f"Possível duplicidade com a reserva ID {exc.duplicate['id']}. "
                    "Marque a confirmação para salvar mesmo assim."
                )
            except Exception as exc:
                st.error("Não foi possível atualizar a reserva.")
                st.exception(exc)


def _delete_reserva(df: pd.DataFrame) -> None:
    if df.empty:
        return
    with st.expander("Excluir reserva"):
        ids = df["id"].astype(int).tolist()
        reserva_id = st.selectbox(
            "Selecione a reserva para excluir",
            ids,
            format_func=lambda item: _reserva_label(df, item),
            key="delete_reserva_id",
        )
        confirm = st.checkbox("Confirmo que desejo excluir definitivamente esta reserva.", key="delete_confirm")
        if st.button("Excluir reserva", type="primary", width="stretch"):
            if not confirm:
                st.warning("Confirme a exclusão antes de continuar.")
                return
            try:
                delete_reserva(int(reserva_id))
                st.success("Reserva excluída.")
                st.rerun()
            except Exception as exc:
                st.error("Não foi possível excluir a reserva.")
                st.exception(exc)


setup_page("Reservas")
bootstrap_database()
render_sidebar(None)
page_header("Reservas", "Consulte, filtre, edite e exporte reservas.")

filters = _build_filters()
df = _prepare_df(list_reservas(filters))
_display_metrics(df)

if df.empty:
    st.info("Nenhuma reserva encontrada para os filtros selecionados.")
else:
    _export_buttons(df)
    page_df = _sort_and_paginate(df)
    st.dataframe(_format_table(page_df), width="stretch", hide_index=True)
    _edit_reserva(df)
    _delete_reserva(df)

