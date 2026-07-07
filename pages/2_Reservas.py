from __future__ import annotations

import unicodedata
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from services.reserva_service import (
    DuplicateReservationError,
    available_years,
    delete_reservas,
    distinct_values,
    get_reserva,
    list_reservas,
    update_reserva,
)
from utils.formatacao import format_currency_br, format_date_br, parse_decimal_br
from utils.ui import bootstrap_database, metric_card, page_header, render_sidebar, setup_page
from utils.validacao import clean_text, parse_date_br, parse_int_positive, validate_reserva


PNG_MAX_ROWS = 120


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
    precisa_padrao_hoje = st.session_state.get("reservas_filtros_padrao_hoje_v1") is not True
    if (
        precisa_padrao_hoje
        or st.session_state.pop("reservas_resetar_para_hoje", False)
        or "reservas_filtros_inicializados" not in st.session_state
    ):
        hoje = date.today()
        st.session_state["f_data_inicio"] = hoje
        st.session_state["f_data_fim"] = hoje
        st.session_state.pop("reservas_filtros_aplicados", None)
        st.session_state["reservas_filtros_inicializados"] = True
        st.session_state["reservas_filtros_padrao_hoje_v1"] = True

    with st.form("reservas_filtros_form"):
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

        col13, col14, col15, col16 = st.columns([1, 1, 1, 1])
        with col13:
            valor_min = parse_decimal_br(st.text_input("Valor mínimo", key="f_valor_min"))
        with col14:
            valor_max = parse_decimal_br(st.text_input("Valor máximo", key="f_valor_max"))
        with col15:
            aplicar = st.form_submit_button("Aplicar filtros", type="primary", width="stretch")
        with col16:
            limpar = st.form_submit_button("Limpar filtros", width="stretch")

        if limpar:
            for key in FILTER_KEYS:
                st.session_state.pop(key, None)
            st.session_state.pop("reservas_filtros_aplicados", None)
            st.session_state["reservas_resetar_para_hoje"] = True
            st.rerun()

    filtros = {
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
    if aplicar or "reservas_filtros_aplicados" not in st.session_state:
        st.session_state["reservas_filtros_aplicados"] = filtros
    return st.session_state["reservas_filtros_aplicados"]


def _prepare_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["data_reserva"] = pd.to_datetime(df["data_reserva"])
    df["ano"] = df["data_reserva"].dt.year
    df["mes"] = df["data_reserva"].dt.month
    df["dia"] = df["data_reserva"].dt.day
    df["hoje_primeiro"] = (df["data_reserva"].dt.date == date.today()).astype(int)
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


def _editable_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    output = pd.DataFrame(
        {
            "Excluir": False,
            "ID": df["id"].astype(int),
            "Data": df["data_reserva"].dt.date,
            "Motorista": df["motorista"].fillna(""),
            "Ajudante": df["ajudante"].fillna(""),
            "Cidade": df["cidade"].fillna(""),
            "Hotel/Pousada": df["hotel_pousada"].fillna(""),
            "Tipo": df["tipo"].fillna(""),
            "Valor": pd.to_numeric(df["valor"], errors="coerce").fillna(0).astype(float),
            "Dias": pd.to_numeric(df["dias"], errors="coerce").fillna(1).astype(int),
            "Nao planejada": df["nao_planejada"].fillna(False).astype(bool),
            "Categoria": df["categoria"].fillna(""),
            "Observacao": df["observacao"].fillna(""),
        }
    )
    return output


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reservas")
    return buffer.getvalue()


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    windows_fonts = Path("C:/Windows/Fonts")
    candidates = [
        windows_fonts / ("arialbd.ttf" if bold else "arial.ttf"),
        windows_fonts / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windows_fonts / ("calibrib.ttf" if bold else "calibri.ttf"),
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _png_text(value: Any) -> str:
    text = str(value or "")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    text = _png_text(text)
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "..."
    while text and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


@st.cache_data(ttl=300, show_spinner=False)
def _to_png_bytes(df: pd.DataFrame) -> bytes:
    if "hoje_primeiro" in df.columns:
        report_df = df.sort_values(["hoje_primeiro", "data_reserva"], ascending=[False, False])
    else:
        report_df = df.sort_values("data_reserva", ascending=False)
    visible_df = report_df.head(PNG_MAX_ROWS).copy()
    total = float(df["valor"].sum()) if not df.empty else 0
    quantidade = len(df)
    hoje = date.today().strftime("%d/%m/%Y")

    width = 1280
    margin = 34
    row_h = 56
    header_h = 206
    table_header_h = 58
    footer_h = 74 if quantidade > PNG_MAX_ROWS else 34
    height = header_h + table_header_h + (len(visible_df) * row_h) + footer_h

    img = Image.new("RGB", (width, height), "#F3F7FB")
    draw = ImageDraw.Draw(img)
    title_font = _font(46, bold=True)
    subtitle_font = _font(22)
    label_font = _font(18, bold=True)
    value_font = _font(36, bold=True)
    head_font = _font(21, bold=True)
    row_font = _font(21)
    small_font = _font(18)

    blue = "#145DA0"
    dark_blue = "#0B3F6F"
    green = "#16A34A"
    border = "#DDE5EE"
    text = "#111827"
    muted = "#D7E7F5"

    draw.rounded_rectangle((margin, 26, width - margin, 168), radius=18, fill=dark_blue)
    draw.rectangle((margin, 142, width - margin, 168), fill=green)
    draw.text((margin + 34, 48), "Reservas de Hotéis", fill="#FFFFFF", font=title_font)
    draw.text((margin + 36, 108), f"Relatório gerado em {hoje}", fill=muted, font=subtitle_font)

    card_w = 260
    card_h = 92
    card_gap = 16
    card_1_x = width - margin - (card_w * 2) - card_gap
    card_2_x = width - margin - card_w
    for x, label, value in (
        (card_1_x, "Valor total", format_currency_br(total)),
        (card_2_x, "Reservas", str(quantidade)),
    ):
        draw.rounded_rectangle((x, 50, x + card_w, 50 + card_h), radius=14, fill="#FFFFFF")
        draw.text((x + 20, 66), _png_text(label.upper()), fill="#64748B", font=label_font)
        draw.text((x + 20, 94), _png_text(value), fill=green if label == "Valor total" else blue, font=value_font)

    y = header_h
    columns = [
        ("Data", 52, 130),
        ("Motorista", 188, 230),
        ("Cidade", 434, 166),
        ("Hotel/Pousada", 620, 285),
        ("Tipo", 920, 118),
        ("Valor", 1052, 135),
        ("Dias", 1194, 52),
    ]
    draw.rounded_rectangle((margin, y - 10, width - margin, y + table_header_h - 10), radius=12, fill=blue)
    draw.rectangle((margin, y + 20, width - margin, y + table_header_h - 10), fill=blue)
    for label, x, _w in columns:
        draw.text((x, y + 7), _png_text(label), fill="#FFFFFF", font=head_font)

    y += table_header_h
    for index, row in visible_df.iterrows():
        fill = "#FFFFFF" if index % 2 == 0 else "#EEF4FA"
        draw.rectangle((margin, y - 2, width - margin, y + row_h - 2), fill=fill)
        draw.line((margin, y + row_h - 2, width - margin, y + row_h - 2), fill=border, width=1)
        values = [
            row["data_reserva"].strftime("%d/%m/%Y"),
            row.get("motorista", ""),
            row.get("cidade", ""),
            row.get("hotel_pousada", ""),
            row.get("tipo", ""),
            format_currency_br(row.get("valor", 0)),
            str(row.get("dias", "")),
        ]
        for value, (_label, x, col_w) in zip(values, columns):
            draw.text((x, y + 15), _fit_text(draw, value, row_font, col_w), fill=text, font=row_font)
        y += row_h

    if quantidade > PNG_MAX_ROWS:
        msg = f"Mostrando as primeiras {PNG_MAX_ROWS} reservas de {quantidade}. Use filtros para gerar uma imagem mais especifica."
        draw.rounded_rectangle((margin, y + 16, width - margin, y + 56), radius=8, fill="#FEF3C7")
        draw.text((margin + 18, y + 25), _png_text(msg), fill="#92400E", font=small_font)

    draw.line((margin, height - 20, width - margin, height - 20), fill="#CBD5E1", width=1)

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _export_buttons(df: pd.DataFrame) -> None:
    formatted = _format_table(df)
    col_csv, col_excel, col_png = st.columns(3)
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
    with col_png:
        st.download_button(
            "Exportar PNG",
            data=_to_png_bytes(df),
            file_name=f"reservas_{date.today().strftime('%Y%m%d')}.png",
            mime="image/png",
            width="stretch",
        )


def _sort_and_paginate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    sort_options = {
        "Hoje primeiro": ["hoje_primeiro", "data_reserva"],
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
    current = st.session_state.get(
        "reservas_ordem_aplicada_v2",
        {"sort_label": "Hoje primeiro", "ascending": False, "page_size": 25, "page": 1},
    )
    if current["sort_label"] not in sort_options:
        current["sort_label"] = "Data"
    if current["page_size"] not in [10, 25, 50, 100]:
        current["page_size"] = 25
    with st.form("reservas_ordem_form"):
        col_sort, col_dir, col_size, col_page, col_apply = st.columns(5)
        with col_sort:
            sort_label = st.selectbox(
                "Ordenar por",
                list(sort_options.keys()),
                index=list(sort_options.keys()).index(current["sort_label"]),
            )
        with col_dir:
            direction = st.selectbox(
                "Direção",
                ["Decrescente", "Crescente"],
                index=1 if current["ascending"] else 0,
            )
        with col_size:
            page_size = st.selectbox(
                "Registros por página",
                [10, 25, 50, 100],
                index=[10, 25, 50, 100].index(current["page_size"]),
            )
        total_pages_form = max(1, (len(df) + page_size - 1) // page_size)
        with col_page:
            page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages_form,
                value=min(int(current["page"]), total_pages_form),
                step=1,
            )
        with col_apply:
            applied = st.form_submit_button("Atualizar tabela", type="primary", width="stretch")

    if applied:
        current = {
            "sort_label": sort_label,
            "ascending": direction == "Crescente",
            "page_size": page_size,
            "page": int(page),
        }
        st.session_state["reservas_ordem_aplicada_v2"] = current

    sort_label = current["sort_label"]
    ascending = current["ascending"]
    page_size = current["page_size"]
    sorted_df = df.sort_values(sort_options[sort_label], ascending=ascending, na_position="last")
    total_pages = max(1, (len(sorted_df) + page_size - 1) // page_size)
    page = min(int(current["page"]), total_pages)
    start = (page - 1) * page_size
    return sorted_df.iloc[start : start + page_size]


def _row_to_reserva_data(row: pd.Series) -> dict[str, Any]:
    dias = parse_int_positive(row.get("Dias")) or 0
    return {
        "data_reserva": parse_date_br(row.get("Data")),
        "motorista": row.get("Motorista", ""),
        "ajudante": row.get("Ajudante", ""),
        "cidade": row.get("Cidade", ""),
        "hotel_pousada": row.get("Hotel/Pousada", ""),
        "tipo": row.get("Tipo", ""),
        "valor": parse_decimal_br(row.get("Valor")),
        "dias": dias,
        "nao_planejada": bool(row.get("Nao planejada")),
        "categoria": row.get("Categoria", ""),
        "observacao": row.get("Observacao", ""),
    }


def _cell_signature(value: Any) -> str:
    if pd.isna(value):
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value).strip()


def _changed_rows(original: pd.DataFrame, edited: pd.DataFrame) -> list[tuple[int, dict[str, Any]]]:
    original_by_id = original.set_index("ID")
    changed: list[tuple[int, dict[str, Any]]] = []
    editable_columns = [col for col in edited.columns if col not in {"Excluir", "ID"}]

    for _, edited_row in edited.iterrows():
        reserva_id = int(edited_row["ID"])
        if reserva_id not in original_by_id.index:
            continue
        original_row = original_by_id.loc[reserva_id]
        has_change = any(_cell_signature(edited_row[col]) != _cell_signature(original_row[col]) for col in editable_columns)
        if has_change:
            changed.append((reserva_id, _row_to_reserva_data(edited_row)))
    return changed


def _render_editable_table(page_df: pd.DataFrame) -> None:
    original = _editable_table(page_df)
    with st.form("reservas_editor_form"):
        edited = st.data_editor(
            original,
            key="reservas_editor",
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            disabled=["ID"],
            column_config={
                "Excluir": st.column_config.CheckboxColumn("Excluir", help="Marque para excluir esta reserva."),
                "ID": st.column_config.NumberColumn("ID", disabled=True),
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
                "Valor": st.column_config.NumberColumn("Valor", min_value=0.01, step=1.0, format="R$ %.2f", required=True),
                "Dias": st.column_config.NumberColumn("Dias", min_value=1, step=1, required=True),
                "Nao planejada": st.column_config.CheckboxColumn("Nao planejada"),
                "Observacao": st.column_config.TextColumn("Observacao", width="medium"),
            },
        )
        col_save, col_delete = st.columns([2, 1])
        with col_save:
            salvar = st.form_submit_button("Salvar alteracoes da tabela", type="primary", width="stretch")
        with col_delete:
            excluir = st.form_submit_button("Excluir selecionadas", width="stretch")

    selected_ids = edited.loc[edited["Excluir"].astype(bool), "ID"].astype(int).tolist()
    if excluir:
        if not selected_ids:
            st.warning("Marque uma ou mais reservas na coluna Excluir.")
            return
        try:
            deleted = delete_reservas(selected_ids)
            st.success(f"{deleted} reserva(s) excluida(s).")
            st.rerun()
        except Exception as exc:
            st.error("Nao foi possivel excluir as reservas selecionadas.")
            st.exception(exc)
        return

    if not salvar:
        return

    changes = _changed_rows(original, edited)
    if not changes:
        st.info("Nenhuma alteração encontrada.")
        return

    errors: list[str] = []
    saved = 0
    for reserva_id, data in changes:
        validation_errors = validate_reserva(data)
        if validation_errors:
            errors.append(f"ID {reserva_id}: {' '.join(validation_errors)}")
            continue
        try:
            update_reserva(reserva_id, data, allow_duplicate=False)
            saved += 1
        except DuplicateReservationError as exc:
            errors.append(f"ID {reserva_id}: possível duplicidade com a reserva ID {exc.duplicate['id']}.")
        except Exception as exc:
            errors.append(f"ID {reserva_id}: nao foi possivel salvar ({exc}).")

    if saved:
        st.success(f"{saved} reserva(s) atualizada(s).")
    for error in errors:
        st.warning(error)
    if saved and not errors:
        st.rerun()


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
            st.warning("Reserva nao encontrada.")
            return

        with st.form(f"edit_reserva_form_{reserva_id}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                data_reserva = st.date_input(
                    "Data", value=reserva["data_reserva"], format="DD/MM/YYYY", key=f"edit_data_{reserva_id}"
                )
                motorista = st.text_input("Motorista", value=reserva["motorista"] or "", key=f"edit_motorista_{reserva_id}")
                ajudante = st.text_input("Ajudante", value=reserva["ajudante"] or "", key=f"edit_ajudante_{reserva_id}")
            with col2:
                cidade = st.text_input("Cidade", value=reserva["cidade"] or "", key=f"edit_cidade_{reserva_id}")
                hotel = st.text_input("Hotel/Pousada", value=reserva["hotel_pousada"] or "", key=f"edit_hotel_{reserva_id}")
                tipo = st.text_input("Tipo", value=reserva["tipo"] or "", key=f"edit_tipo_{reserva_id}")
            with col3:
                valor = st.text_input("Valor", value=format_currency_br(reserva["valor"]), key=f"edit_valor_{reserva_id}")
                dias = st.number_input("Dias", min_value=1, value=int(reserva["dias"]), step=1, key=f"edit_dias_{reserva_id}")
                nao_planejada = st.checkbox(
                    "Nao planejada", value=bool(reserva["nao_planejada"]), key=f"edit_np_{reserva_id}"
                )
            categoria = st.text_input("Categoria", value=reserva["categoria"] or "", key=f"edit_categoria_{reserva_id}")
            observacao = st.text_area(
                "Observacao", value=reserva["observacao"] or "", height=90, key=f"edit_obs_{reserva_id}"
            )
            allow_duplicate = st.checkbox(
                "Salvar mesmo que exista possivel duplicidade", key=f"edit_allow_dup_{reserva_id}"
            )
            submitted = st.form_submit_button("Salvar alteracoes", type="primary", width="stretch")

        if submitted:
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
                    f"Possivel duplicidade com a reserva ID {exc.duplicate['id']}. "
                    "Marque a confirmacao para salvar mesmo assim."
                )
            except Exception as exc:
                st.error("Nao foi possivel atualizar a reserva.")
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
    _render_editable_table(page_df)

