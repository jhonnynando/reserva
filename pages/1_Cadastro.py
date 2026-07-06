from __future__ import annotations

from datetime import date

import streamlit as st

from services.reserva_service import DuplicateReservationError, create_reserva
from utils.formatacao import format_currency_br, parse_decimal_br
from utils.ui import bootstrap_database, page_header, render_sidebar, setup_page
from utils.validacao import validate_reserva


def _build_reserva_payload(prefix: str) -> dict:
    valor = parse_decimal_br(st.session_state.get(f"{prefix}_valor"))
    return {
        "data_reserva": st.session_state.get(f"{prefix}_data"),
        "motorista": st.session_state.get(f"{prefix}_motorista", ""),
        "ajudante": st.session_state.get(f"{prefix}_ajudante", ""),
        "cidade": st.session_state.get(f"{prefix}_cidade", ""),
        "hotel_pousada": st.session_state.get(f"{prefix}_hotel", ""),
        "tipo": st.session_state.get(f"{prefix}_tipo", ""),
        "valor": valor,
        "dias": int(st.session_state.get(f"{prefix}_dias") or 0),
        "nao_planejada": bool(st.session_state.get(f"{prefix}_nao_planejada")),
        "categoria": st.session_state.get(f"{prefix}_categoria", ""),
        "observacao": st.session_state.get(f"{prefix}_observacao", ""),
    }


def _save_reserva(data: dict, allow_duplicate: bool = False) -> None:
    errors = validate_reserva(data)
    if errors:
        for error in errors:
            st.warning(error)
        return

    try:
        create_reserva(data, None, allow_duplicate=allow_duplicate)
        st.session_state.pop("reserva_pendente", None)
        st.session_state["cadastro_form_version"] = st.session_state.get("cadastro_form_version", 0) + 1
        st.success(f"Reserva salva com sucesso: {format_currency_br(data['valor'])}.")
        st.rerun()
    except DuplicateReservationError as exc:
        st.session_state["reserva_pendente"] = data
        st.warning(
            f"Possivel duplicidade encontrada com a reserva ID {exc.duplicate['id']}. "
            "Confirme abaixo se deseja salvar mesmo assim."
        )
    except Exception as exc:
        st.error("Nao foi possivel salvar a reserva.")
        st.exception(exc)


setup_page("Cadastro")
bootstrap_database()
render_sidebar(None)
page_header("Cadastro de reserva", "Escreva os dados da reserva para salvar no sistema.")

version = st.session_state.get("cadastro_form_version", 0)
prefix = f"form_reserva_{version}"

col1, col2, col3 = st.columns(3)

with col1:
    st.date_input("Data", value=date.today(), key=f"{prefix}_data", format="DD/MM/YYYY")
    st.text_input("Motorista", placeholder="Escreva o nome do motorista", key=f"{prefix}_motorista")
    st.text_input("Ajudante", placeholder="Escreva o nome do ajudante, se houver", key=f"{prefix}_ajudante")

with col2:
    st.text_input("Cidade", placeholder="Escreva a cidade", key=f"{prefix}_cidade")
    st.text_input("Hotel/Pousada", placeholder="Escreva o hotel ou pousada", key=f"{prefix}_hotel")
    st.text_input("Tipo", placeholder="Escreva o tipo", key=f"{prefix}_tipo")

with col3:
    st.number_input("Valor", min_value=0.0, step=10.0, format="%.2f", key=f"{prefix}_valor")
    valor_atual = parse_decimal_br(st.session_state.get(f"{prefix}_valor"))
    st.caption(f"Valor informado: {format_currency_br(valor_atual)}")
    st.number_input("Dias", min_value=1, step=1, value=1, key=f"{prefix}_dias")
    st.checkbox("Nao planejada", key=f"{prefix}_nao_planejada")

st.text_input("Categoria", placeholder="Escreva a categoria", key=f"{prefix}_categoria")
st.text_area("Observacao", height=110, key=f"{prefix}_observacao")

reserva_data = _build_reserva_payload(prefix)

if st.button("Salvar reserva", type="primary", width="stretch"):
    _save_reserva(reserva_data)

pending = st.session_state.get("reserva_pendente")
if pending:
    st.warning("Existe uma possivel duplicidade pendente de confirmacao.")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Salvar mesmo assim", type="primary", width="stretch"):
            _save_reserva(pending, allow_duplicate=True)
    with cancel_col:
        if st.button("Cancelar salvamento", width="stretch"):
            st.session_state.pop("reserva_pendente", None)
            st.info("Salvamento cancelado.")
            st.rerun()
