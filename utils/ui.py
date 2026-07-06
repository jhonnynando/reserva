from __future__ import annotations

from typing import Any

import streamlit as st


def setup_page(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} | Reservas de Hotéis",
        page_icon="hotel",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --app-blue: #145DA0;
            --app-blue-dark: #0B3558;
            --app-green: #16A34A;
            --app-bg: #F5F7FA;
            --app-border: #DDE5EE;
            --app-text: #1F2937;
        }
        .stApp {
            background: var(--app-bg);
        }
        .block-container {
            padding-top: 1.35rem;
            padding-bottom: 2rem;
            max-width: 1440px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0B3558 0%, #145DA0 100%);
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF;
        }
        [data-testid="stSidebar"] .stButton button {
            border: 1px solid rgba(255,255,255,.25);
            background: rgba(255,255,255,.08);
            color: #FFFFFF;
        }
        .app-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            padding: 1rem 1.15rem;
            border: 1px solid var(--app-border);
            border-radius: 8px;
            background: #FFFFFF;
            margin-bottom: 1rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, .05);
        }
        .app-header h1 {
            font-size: 1.45rem;
            color: var(--app-blue-dark);
            margin: 0;
            letter-spacing: 0;
        }
        .app-header p {
            color: #64748B;
            margin: .25rem 0 0;
            font-size: .95rem;
        }
        .sidebar-brand {
            font-size: 1.15rem;
            font-weight: 700;
            margin: .75rem 0 1rem;
        }
        .user-box {
            border: 1px solid rgba(255,255,255,.22);
            border-radius: 8px;
            padding: .75rem;
            background: rgba(255,255,255,.08);
            margin-bottom: .85rem;
        }
        .metric-card {
            padding: .95rem 1rem;
            background: #FFFFFF;
            border: 1px solid var(--app-border);
            border-left: 4px solid var(--app-blue);
            border-radius: 8px;
            min-height: 96px;
            box-shadow: 0 8px 20px rgba(15, 23, 42, .04);
        }
        .metric-card.green {
            border-left-color: var(--app-green);
        }
        .metric-label {
            color: #64748B;
            font-size: .82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0;
            margin-bottom: .35rem;
        }
        .metric-value {
            color: var(--app-text);
            font-size: clamp(1.15rem, 2vw, 1.65rem);
            line-height: 1.2;
            font-weight: 750;
            word-break: break-word;
        }
        .section-card {
            background: #FFFFFF;
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 8px 20px rgba(15, 23, 42, .04);
        }
        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: .75rem;
        }
        .stButton button[kind="primary"] {
            background: var(--app-blue);
            border-color: var(--app-blue);
        }
        @media (max-width: 760px) {
            .app-header {
                display: block;
            }
            .metric-card {
                min-height: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(user: dict[str, Any] | None) -> None:
    with st.sidebar:
        st.markdown("<div class='sidebar-brand'>Reservas de Hotéis</div>", unsafe_allow_html=True)
        if user:
            st.markdown(
                f"""
                <div class="user-box">
                    <strong>{user.get("nome", "")}</strong><br>
                    <span>{user.get("email", "")}</span><br>
                    <small>Perfil: {user.get("perfil", "")}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )


def bootstrap_database() -> None:
    from database import DatabaseConfigurationError, initialize_database

    try:
        initialize_database()
    except DatabaseConfigurationError as exc:
        st.error(str(exc))
        st.info("Configure DATABASE_URL no arquivo .env local ou nos secrets da plataforma de publicação.")
        st.stop()
    except Exception as exc:
        st.error("Não foi possível inicializar o banco de dados.")
        st.exception(exc)
        st.stop()


def page_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <div>
                <h1>{title}</h1>
                <p>{subtitle or ""}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, accent: str = "blue") -> None:
    css_class = "metric-card green" if accent == "green" else "metric-card"
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

