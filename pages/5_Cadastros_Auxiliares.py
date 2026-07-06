from __future__ import annotations

import pandas as pd
import streamlit as st

from services.reserva_service import (
    add_ajudante,
    add_cidade,
    add_hotel,
    add_motorista,
    list_ajudantes,
    list_cidades,
    list_hoteis,
    list_motoristas,
    update_ajudante,
    update_cidade,
    update_hotel,
    update_motorista,
)
from utils.ui import bootstrap_database, page_header, render_sidebar, setup_page
from utils.validacao import clean_text


def _cidade_label(cidade: dict) -> str:
    estado = f" - {cidade['estado']}" if cidade.get("estado") else ""
    return f"{cidade['nome']}{estado}"


def _status_text(value: bool) -> str:
    return "Ativo" if value else "Inativo"


def _show_table(items: list[dict], columns: dict[str, str]) -> None:
    if not items:
        st.info("Nenhum cadastro encontrado.")
        return
    df = pd.DataFrame(items)
    df["ativo"] = df["ativo"].map(_status_text)
    st.dataframe(df.rename(columns=columns), width="stretch", hide_index=True)


def _motoristas_tab() -> None:
    st.subheader("Motoristas")
    search = st.text_input("Pesquisar motorista", key="search_motorista")
    items = list_motoristas(active_only=False, search=search)
    with st.form("add_motorista_form"):
        nome = st.text_input("Novo motorista")
        submitted = st.form_submit_button("Adicionar", type="primary", width="stretch")
    if submitted:
        if clean_text(nome):
            add_motorista(nome)
            st.success("Motorista cadastrado.")
            st.rerun()
        st.warning("Informe o nome.")

    _show_table(items, {"id": "ID", "nome": "Nome", "ativo": "Status"})
    if items:
        selected = st.selectbox("Editar motorista", items, format_func=lambda item: item["nome"])
        with st.form("edit_motorista_form"):
            nome_edit = st.text_input("Nome", value=selected["nome"])
            ativo = st.checkbox("Ativo", value=bool(selected["ativo"]))
            submitted_edit = st.form_submit_button("Salvar alterações", type="primary", width="stretch")
        if submitted_edit:
            update_motorista(int(selected["id"]), nome_edit, ativo)
            st.success("Motorista atualizado.")
            st.rerun()


def _ajudantes_tab() -> None:
    st.subheader("Ajudantes")
    search = st.text_input("Pesquisar ajudante", key="search_ajudante")
    items = list_ajudantes(active_only=False, search=search)
    with st.form("add_ajudante_form"):
        nome = st.text_input("Novo ajudante")
        submitted = st.form_submit_button("Adicionar", type="primary", width="stretch")
    if submitted:
        if clean_text(nome):
            add_ajudante(nome)
            st.success("Ajudante cadastrado.")
            st.rerun()
        st.warning("Informe o nome.")

    _show_table(items, {"id": "ID", "nome": "Nome", "ativo": "Status"})
    if items:
        selected = st.selectbox("Editar ajudante", items, format_func=lambda item: item["nome"])
        with st.form("edit_ajudante_form"):
            nome_edit = st.text_input("Nome", value=selected["nome"])
            ativo = st.checkbox("Ativo", value=bool(selected["ativo"]))
            submitted_edit = st.form_submit_button("Salvar alterações", type="primary", width="stretch")
        if submitted_edit:
            update_ajudante(int(selected["id"]), nome_edit, ativo)
            st.success("Ajudante atualizado.")
            st.rerun()


def _cidades_tab() -> None:
    st.subheader("Cidades")
    search = st.text_input("Pesquisar cidade", key="search_cidade")
    items = list_cidades(active_only=False, search=search)
    with st.form("add_cidade_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            nome = st.text_input("Nova cidade")
        with col2:
            estado = st.text_input("UF", max_chars=2)
        submitted = st.form_submit_button("Adicionar", type="primary", width="stretch")
    if submitted:
        if clean_text(nome):
            add_cidade(nome, estado)
            st.success("Cidade cadastrada.")
            st.rerun()
        st.warning("Informe o nome.")

    _show_table(items, {"id": "ID", "nome": "Nome", "estado": "UF", "ativo": "Status"})
    if items:
        selected = st.selectbox("Editar cidade", items, format_func=_cidade_label)
        with st.form("edit_cidade_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                nome_edit = st.text_input("Nome", value=selected["nome"])
            with col2:
                estado_edit = st.text_input("UF", value=selected.get("estado") or "", max_chars=2)
            ativo = st.checkbox("Ativo", value=bool(selected["ativo"]))
            submitted_edit = st.form_submit_button("Salvar alterações", type="primary", width="stretch")
        if submitted_edit:
            update_cidade(int(selected["id"]), nome_edit, estado_edit, ativo)
            st.success("Cidade atualizada.")
            st.rerun()


def _hoteis_tab() -> None:
    st.subheader("Hotéis/Pousadas")
    cidades = list_cidades(active_only=True)
    search = st.text_input("Pesquisar hotel/pousada", key="search_hotel")
    items = list_hoteis(active_only=False, search=search)
    with st.form("add_hotel_form"):
        cidade = st.selectbox("Cidade", cidades, index=None, format_func=_cidade_label)
        nome = st.text_input("Novo hotel/pousada")
        telefone = st.text_input("Telefone")
        observacao = st.text_area("Observação", height=80)
        submitted = st.form_submit_button("Adicionar", type="primary", width="stretch")
    if submitted:
        if not cidade:
            st.warning("Selecione a cidade.")
        elif clean_text(nome):
            add_hotel(nome, int(cidade["id"]), telefone, observacao)
            st.success("Hotel/Pousada cadastrado.")
            st.rerun()
        else:
            st.warning("Informe o nome.")

    _show_table(
        items,
        {
            "id": "ID",
            "nome": "Nome",
            "cidade": "Cidade",
            "estado": "UF",
            "telefone": "Telefone",
            "observacao": "Observação",
            "ativo": "Status",
            "cidade_id": "Cidade ID",
        },
    )
    if items:
        selected = st.selectbox("Editar hotel/pousada", items, format_func=lambda item: item["nome"])
        current_index = next(
            (idx for idx, cidade in enumerate(cidades) if cidade["id"] == selected.get("cidade_id")),
            None,
        )
        with st.form("edit_hotel_form"):
            cidade_edit = st.selectbox(
                "Cidade",
                cidades,
                index=current_index,
                format_func=_cidade_label,
            )
            nome_edit = st.text_input("Nome", value=selected["nome"])
            telefone_edit = st.text_input("Telefone", value=selected.get("telefone") or "")
            observacao_edit = st.text_area("Observação", value=selected.get("observacao") or "", height=80)
            ativo = st.checkbox("Ativo", value=bool(selected["ativo"]))
            submitted_edit = st.form_submit_button("Salvar alterações", type="primary", width="stretch")
        if submitted_edit:
            update_hotel(
                int(selected["id"]),
                nome_edit,
                int(cidade_edit["id"]) if cidade_edit else None,
                telefone_edit,
                observacao_edit,
                ativo,
            )
            st.success("Hotel/Pousada atualizado.")
            st.rerun()


setup_page("Cadastros Auxiliares")
bootstrap_database()
render_sidebar(None)
page_header("Cadastros auxiliares", "Mantenha motoristas, ajudantes, cidades e hotéis/pousadas.")

tab1, tab2, tab3, tab4 = st.tabs(["Motoristas", "Ajudantes", "Cidades", "Hotéis/Pousadas"])
with tab1:
    _motoristas_tab()
with tab2:
    _ajudantes_tab()
with tab3:
    _cidades_tab()
with tab4:
    _hoteis_tab()

