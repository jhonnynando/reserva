from __future__ import annotations

import pandas as pd
import streamlit as st

from services.importacao_service import (
    get_sheet_names,
    import_records,
    mark_duplicates,
    parse_excel,
)
from utils.formatacao import format_currency_br
from utils.ui import bootstrap_database, metric_card, page_header, render_sidebar, setup_page


def _preview_dataframe(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    output = df[
        [
            "__aba",
            "__linha",
            "data_reserva",
            "motorista",
            "ajudante",
            "cidade",
            "hotel_pousada",
            "tipo",
            "valor",
            "dias",
            "nao_planejada",
            "categoria",
            "duplicado",
            "id_existente",
        ]
    ].copy()
    output["data_reserva"] = pd.to_datetime(output["data_reserva"]).dt.strftime("%d/%m/%Y")
    output["valor"] = output["valor"].apply(format_currency_br)
    output["nao_planejada"] = output["nao_planejada"].map({True: "Sim", False: "Não"})
    output["duplicado"] = output["duplicado"].map({True: "Sim", False: "Não"})
    output = output.rename(
        columns={
            "__aba": "Aba",
            "__linha": "Linha",
            "data_reserva": "Data",
            "motorista": "Motorista",
            "ajudante": "Ajudante",
            "cidade": "Cidade",
            "hotel_pousada": "Hotel/Pousada",
            "tipo": "Tipo",
            "valor": "Valor",
            "dias": "Dias",
            "nao_planejada": "Não planejada",
            "categoria": "Categoria",
            "duplicado": "Duplicado",
            "id_existente": "ID existente",
        }
    )
    return output


setup_page("Importar Excel")
bootstrap_database()
render_sidebar(None)
page_header("Importar Excel", "Importe planilhas .xlsx com validação antes da gravação.")

uploaded_file = st.file_uploader("Arquivo .xlsx", type=["xlsx"])

if uploaded_file:
    try:
        sheets = get_sheet_names(uploaded_file)
    except Exception as exc:
        st.error("Não foi possível ler as abas da planilha.")
        st.exception(exc)
        st.stop()

    default_sheets = [sheet for sheet in sheets if sheet.upper() in {"HOTEIS2025", "HOTEIS2026"}] or sheets
    selected_sheets = st.multiselect("Abas para importar", sheets, default=default_sheets)

    if st.button("Analisar planilha", type="primary", width="stretch"):
        if not selected_sheets:
            st.warning("Selecione pelo menos uma aba.")
        else:
            try:
                preview = parse_excel(uploaded_file, selected_sheets)
                marked_records = mark_duplicates(preview.records)
                st.session_state["importacao_preview"] = {
                    "records": marked_records,
                    "errors": preview.errors,
                    "arquivo": uploaded_file.name,
                    "abas": selected_sheets,
                }
                st.success("Análise concluída.")
            except Exception as exc:
                st.error("Erro ao analisar a planilha.")
                st.exception(exc)

preview_state = st.session_state.get("importacao_preview")
if preview_state:
    records = preview_state["records"]
    errors = preview_state["errors"]
    duplicados = sum(1 for item in records if item.get("duplicado"))

    cols = st.columns(4)
    with cols[0]:
        metric_card("Registros válidos", str(len(records)), accent="green")
    with cols[1]:
        metric_card("Registros com erro", str(len(errors)))
    with cols[2]:
        metric_card("Duplicados", str(duplicados))
    with cols[3]:
        metric_card("Abas", str(len(preview_state["abas"])))

    if records:
        st.subheader("Prévia dos registros válidos")
        st.dataframe(_preview_dataframe(records).head(200), width="stretch", hide_index=True)

    if errors:
        st.subheader("Linhas com erro")
        st.dataframe(pd.DataFrame(errors), width="stretch", hide_index=True)

    st.subheader("Gravação")
    atualizar_existentes = st.checkbox("Atualizar registros existentes quando houver duplicidade")
    ignorar_duplicados = st.checkbox(
        "Ignorar duplicados",
        value=not atualizar_existentes,
        disabled=atualizar_existentes,
    )
    if atualizar_existentes:
        ignorar_duplicados = False

    if st.button("Importar registros válidos", type="primary", width="stretch"):
        if not records:
            st.warning("Não há registros válidos para importar.")
        else:
            try:
                result = import_records(
                    records=records,
                    user_id=None,
                    arquivo=preview_state["arquivo"],
                    abas=preview_state["abas"],
                    ignorar_duplicados=ignorar_duplicados,
                    atualizar_existentes=atualizar_existentes,
                )
                st.session_state.pop("importacao_preview", None)
                st.success(
                    "Importação concluída. "
                    f"Importados: {result['importados']}. "
                    f"Atualizados: {result['atualizados']}. "
                    f"Ignorados: {result['ignorados']}."
                )
            except Exception as exc:
                st.error("A importação foi cancelada e nenhum lote parcial foi mantido.")
                st.exception(exc)
else:
    st.info("Envie uma planilha para iniciar a análise.")

