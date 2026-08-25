from __future__ import annotations

from typing import Any

import streamlit as st


def setup_page(title: str) -> None:
    st.set_page_config(
        page_title=f"{title} | Reservas de Hotéis",
        page_icon="hotel",
        layout="wide",
        initial_sidebar_state="auto",
    )
    inject_css()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --app-blue: #1967D2;
            --app-blue-dark: #0A3157;
            --app-cyan: #24B7C7;
            --app-green: #17A673;
            --app-bg: #EDF4FA;
            --app-border: rgba(255, 255, 255, .76);
            --app-text: #102A43;
            --app-muted: #627D98;
            --glass: rgba(255, 255, 255, .66);
            --glass-strong: rgba(255, 255, 255, .82);
            --glass-border: rgba(255, 255, 255, .88);
            --glass-shadow: 0 18px 44px rgba(31, 73, 110, .10);
        }
        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .stApp {
            color: var(--app-text);
            background:
                radial-gradient(circle at 8% 4%, rgba(36, 183, 199, .16), transparent 28rem),
                radial-gradient(circle at 92% 8%, rgba(25, 103, 210, .14), transparent 32rem),
                radial-gradient(circle at 72% 88%, rgba(71, 196, 153, .10), transparent 28rem),
                linear-gradient(145deg, #F4F9FD 0%, #EAF2F8 48%, #F6FAFD 100%);
            background-attachment: fixed;
        }
        [data-testid="stHeader"] {
            background: rgba(244, 249, 253, .72);
            border-bottom: 1px solid rgba(255, 255, 255, .78);
            backdrop-filter: blur(16px) saturate(130%);
            -webkit-backdrop-filter: blur(16px) saturate(130%);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1520px;
        }
        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 18% 8%, rgba(72, 199, 213, .25), transparent 18rem),
                linear-gradient(165deg, rgba(8, 42, 72, .98) 0%, rgba(12, 66, 111, .96) 58%, rgba(13, 91, 129, .94) 100%);
            border-right: 1px solid rgba(255, 255, 255, .18);
            box-shadow: 16px 0 42px rgba(15, 52, 82, .14);
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: .8rem;
        }
        .sidebar-brand-card {
            display: flex;
            align-items: center;
            gap: .8rem;
            padding: .85rem;
            margin: .25rem 0 1.25rem;
            border: 1px solid rgba(255, 255, 255, .20);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(255, 255, 255, .16), rgba(255, 255, 255, .07));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .20), 0 14px 32px rgba(0, 21, 40, .16);
            backdrop-filter: blur(14px) saturate(130%);
            -webkit-backdrop-filter: blur(14px) saturate(130%);
        }
        .sidebar-brand-mark {
            display: grid;
            place-items: center;
            width: 42px;
            height: 42px;
            flex: 0 0 42px;
            border-radius: 14px;
            color: #083556 !important;
            font-weight: 850;
            letter-spacing: -.04em;
            background: linear-gradient(145deg, rgba(255, 255, 255, .98), rgba(209, 245, 248, .88));
            box-shadow: 0 9px 22px rgba(0, 18, 36, .18), inset 0 1px 0 #FFFFFF;
        }
        .sidebar-brand-title {
            font-size: 1rem;
            font-weight: 760;
            line-height: 1.15;
        }
        .sidebar-brand-subtitle {
            margin-top: .22rem;
            color: rgba(232, 246, 255, .72) !important;
            font-size: .72rem;
            letter-spacing: .02em;
        }
        .sidebar-section-label {
            margin: 1rem .55rem .45rem;
            color: rgba(218, 239, 251, .62) !important;
            font-size: .67rem;
            font-weight: 750;
            letter-spacing: .14em;
            text-transform: uppercase;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] {
            margin-bottom: .28rem;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            min-height: 43px;
            padding: .58rem .72rem;
            border: 1px solid transparent;
            border-radius: 13px;
            color: rgba(245, 251, 255, .84) !important;
            font-weight: 590;
            transition: background .18s ease, border-color .18s ease, transform .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            border-color: rgba(255, 255, 255, .17);
            background: rgba(255, 255, 255, .10);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
            border-color: rgba(255, 255, 255, .28);
            background: linear-gradient(135deg, rgba(255, 255, 255, .22), rgba(255, 255, 255, .11));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16), 0 10px 24px rgba(0, 23, 44, .12);
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"]:has(a[href*="Reservas"]) a,
        [data-testid="stSidebar"] [data-testid="stPageLink"]:has(a[href*="Dashboard"]) a {
            border-color: rgba(152, 231, 239, .16);
            background: rgba(95, 206, 216, .08);
            color: #FFFFFF !important;
            font-weight: 720;
        }
        .sidebar-footer {
            display: flex;
            align-items: center;
            gap: .45rem;
            margin: 1.35rem .5rem 0;
            color: rgba(218, 239, 251, .62) !important;
            font-size: .72rem;
        }
        .sidebar-footer-dot,
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: #55D6A6;
            box-shadow: 0 0 0 4px rgba(85, 214, 166, .13);
        }
        [data-testid="stSidebar"] .stButton button {
            border: 1px solid rgba(255,255,255,.25);
            background: rgba(255,255,255,.09);
            color: #FFFFFF;
        }
        .app-header {
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1.15rem 1.3rem;
            border: 1px solid var(--glass-border);
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(255, 255, 255, .82), rgba(255, 255, 255, .55));
            margin-bottom: 1.15rem;
            box-shadow: var(--glass-shadow), inset 0 1px 0 rgba(255, 255, 255, .94);
            backdrop-filter: blur(18px) saturate(135%);
            -webkit-backdrop-filter: blur(18px) saturate(135%);
        }
        .app-header::after {
            content: "";
            position: absolute;
            width: 240px;
            height: 240px;
            right: -70px;
            top: -150px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(52, 183, 205, .20), transparent 68%);
            pointer-events: none;
        }
        .app-header-main {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: .9rem;
        }
        .app-header-icon {
            display: grid;
            place-items: center;
            width: 46px;
            height: 46px;
            flex: 0 0 46px;
            border: 1px solid rgba(255, 255, 255, .94);
            border-radius: 15px;
            color: #FFFFFF;
            font-size: 1.05rem;
            font-weight: 820;
            background: linear-gradient(145deg, var(--app-blue), var(--app-cyan));
            box-shadow: 0 10px 24px rgba(25, 103, 210, .20), inset 0 1px 0 rgba(255, 255, 255, .30);
        }
        .app-header-eyebrow {
            color: #3B82A0;
            font-size: .65rem;
            font-weight: 780;
            letter-spacing: .13em;
            text-transform: uppercase;
        }
        .app-header h1 {
            font-size: clamp(1.35rem, 2vw, 1.72rem);
            color: var(--app-blue-dark);
            margin: .08rem 0 0;
            letter-spacing: -.025em;
        }
        .app-header p {
            color: var(--app-muted);
            margin: .18rem 0 0;
            font-size: .88rem;
        }
        .app-header-status {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: .5rem;
            flex: 0 0 auto;
            padding: .46rem .68rem;
            border: 1px solid rgba(255, 255, 255, .92);
            border-radius: 999px;
            color: #486581;
            font-size: .72rem;
            font-weight: 650;
            background: rgba(255, 255, 255, .52);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .88);
        }
        .user-box {
            border: 1px solid rgba(255,255,255,.22);
            border-radius: 16px;
            padding: .75rem;
            background: rgba(255,255,255,.08);
            margin-bottom: .85rem;
        }
        .metric-card {
            position: relative;
            overflow: hidden;
            padding: 1rem 1.05rem;
            min-height: 102px;
            border: 1px solid var(--glass-border);
            border-radius: 18px;
            background: linear-gradient(145deg, rgba(255, 255, 255, .82), rgba(255, 255, 255, .58));
            box-shadow: 0 14px 32px rgba(31, 73, 110, .08), inset 0 1px 0 rgba(255, 255, 255, .94);
            backdrop-filter: blur(14px) saturate(125%);
            -webkit-backdrop-filter: blur(14px) saturate(125%);
        }
        .metric-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 18px;
            right: 18px;
            height: 3px;
            border-radius: 0 0 999px 999px;
            background: linear-gradient(90deg, var(--app-blue), var(--app-cyan));
            opacity: .88;
        }
        .metric-card::after {
            content: "";
            position: absolute;
            width: 85px;
            height: 85px;
            right: -35px;
            bottom: -46px;
            border-radius: 999px;
            background: rgba(36, 183, 199, .10);
        }
        .metric-card.green::before {
            background: linear-gradient(90deg, var(--app-green), #5ED8AB);
        }
        .metric-card.green::after {
            background: rgba(23, 166, 115, .11);
        }
        .metric-label {
            position: relative;
            z-index: 1;
            color: var(--app-muted);
            font-size: .73rem;
            font-weight: 720;
            text-transform: uppercase;
            letter-spacing: .045em;
            margin: .15rem 0 .45rem;
        }
        .metric-value {
            position: relative;
            z-index: 1;
            color: var(--app-text);
            font-size: clamp(1.12rem, 1.8vw, 1.58rem);
            line-height: 1.2;
            font-weight: 780;
            letter-spacing: -.025em;
            word-break: break-word;
        }
        .section-card {
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 18px;
            padding: 1rem;
            box-shadow: var(--glass-shadow);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
        }
        div[data-testid="stForm"],
        div[data-testid="stExpander"] {
            border: 1px solid var(--glass-border) !important;
            border-radius: 18px !important;
            background: linear-gradient(145deg, rgba(255, 255, 255, .72), rgba(255, 255, 255, .50)) !important;
            box-shadow: 0 14px 34px rgba(31, 73, 110, .07), inset 0 1px 0 rgba(255, 255, 255, .90);
            backdrop-filter: blur(14px) saturate(125%);
            -webkit-backdrop-filter: blur(14px) saturate(125%);
        }
        div[data-testid="stMetric"] {
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 18px;
            padding: .75rem;
        }
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] > div,
        [data-testid="stNumberInput"] [data-baseweb="input"] > div {
            border-color: rgba(133, 165, 190, .22) !important;
            border-radius: 12px !important;
            background: rgba(255, 255, 255, .57) !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .84);
        }
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within {
            border-color: rgba(25, 103, 210, .55) !important;
            box-shadow: 0 0 0 3px rgba(25, 103, 210, .09) !important;
        }
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            min-height: 2.55rem;
            border: 1px solid rgba(139, 170, 194, .28) !important;
            border-radius: 12px !important;
            color: var(--app-blue-dark) !important;
            font-weight: 670 !important;
            background: rgba(255, 255, 255, .62) !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .92), 0 8px 18px rgba(31, 73, 110, .06);
            transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            border-color: rgba(25, 103, 210, .34) !important;
            transform: translateY(-1px);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .95), 0 11px 24px rgba(31, 73, 110, .10);
        }
        button[kind^="primary"] {
            border-color: rgba(25, 103, 210, .48) !important;
            color: #FFFFFF !important;
            background: linear-gradient(135deg, #1967D2, #159BB6) !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .24), 0 10px 24px rgba(25, 103, 210, .20) !important;
        }
        button[kind^="primary"]:hover {
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .28), 0 13px 28px rgba(25, 103, 210, .26) !important;
        }
        button[kind^="primary"] p,
        button[kind^="primary"] span {
            color: #FFFFFF !important;
        }
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"],
        [data-testid="stPlotlyChart"] {
            overflow: hidden;
            border: 1px solid var(--glass-border);
            border-radius: 18px;
            background: rgba(255, 255, 255, .60);
            box-shadow: 0 14px 34px rgba(31, 73, 110, .07), inset 0 1px 0 rgba(255, 255, 255, .88);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }
        [data-testid="stPlotlyChart"] {
            padding: .35rem;
        }
        [data-testid="stAlert"] {
            border: 1px solid rgba(255, 255, 255, .88);
            border-radius: 15px;
            background: rgba(255, 255, 255, .66);
            box-shadow: 0 10px 24px rgba(31, 73, 110, .06);
        }
        .main-section-heading {
            margin: 1.3rem 0 .65rem;
        }
        .main-section-heading span {
            display: block;
            margin-bottom: .18rem;
            color: #3B82A0;
            font-size: .66rem;
            font-weight: 780;
            letter-spacing: .13em;
            text-transform: uppercase;
        }
        .main-section-heading strong {
            color: var(--app-blue-dark);
            font-size: 1.05rem;
            letter-spacing: -.015em;
        }
        [data-testid="stMain"] [data-testid="stPageLink"] a {
            min-height: 64px;
            padding: .85rem 1rem;
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            color: var(--app-blue-dark) !important;
            font-weight: 700;
            background: linear-gradient(145deg, rgba(255, 255, 255, .78), rgba(255, 255, 255, .53));
            box-shadow: 0 12px 28px rgba(31, 73, 110, .07), inset 0 1px 0 rgba(255, 255, 255, .92);
            transition: transform .17s ease, box-shadow .17s ease, border-color .17s ease;
        }
        [data-testid="stMain"] [data-testid="stPageLink"] a:hover {
            border-color: rgba(25, 103, 210, .28);
            transform: translateY(-2px);
            box-shadow: 0 16px 32px rgba(31, 73, 110, .11), inset 0 1px 0 rgba(255, 255, 255, .94);
        }
        [data-testid="stToggle"] label,
        [data-testid="stCheckbox"] label {
            font-weight: 610;
            color: var(--app-text);
        }
        h1, h2, h3 {
            color: var(--app-blue-dark);
            letter-spacing: -.025em;
        }
        h3 {
            font-size: 1.08rem;
        }
        p, label, [data-testid="stCaptionContainer"] {
            color: var(--app-muted);
        }
        @supports not ((backdrop-filter: blur(8px)) or (-webkit-backdrop-filter: blur(8px))) {
            .app-header,
            .metric-card,
            div[data-testid="stForm"],
            [data-testid="stPlotlyChart"] {
                background: rgba(255, 255, 255, .92) !important;
            }
        }
        @media (max-width: 760px) {
            .block-container {
                padding-top: 1rem;
            }
            .app-header {
                align-items: flex-start;
                padding: 1rem;
                border-radius: 18px;
            }
            .app-header-status {
                display: none;
            }
            .app-header-icon {
                width: 40px;
                height: 40px;
                flex-basis: 40px;
            }
            .metric-card {
                min-height: auto;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(user: dict[str, Any] | None, current_page: str | None = None) -> None:
    with st.sidebar:
        current_href = {
            "Reservas": "Reservas",
            "Dashboard": "Dashboard",
            "Cadastro": "Cadastro",
            "Importar Excel": "Importar_Excel",
            "Inicio": "",
        }.get(current_page)
        if current_href is not None:
            st.markdown(
                f"""
                <style>
                [data-testid="stSidebar"] [data-testid="stPageLink"] a[href="{current_href}"] {{
                    border-color: rgba(255, 255, 255, .34) !important;
                    background: linear-gradient(135deg, rgba(255, 255, 255, .24), rgba(255, 255, 255, .12)) !important;
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .18), 0 10px 24px rgba(0, 23, 44, .14) !important;
                    color: #FFFFFF !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            """
            <div class="sidebar-brand-card">
                <div class="sidebar-brand-mark">RH</div>
                <div>
                    <div class="sidebar-brand-title">Reservas de Hotéis</div>
                    <div class="sidebar-brand-subtitle">Gestão de hospedagens</div>
                </div>
            </div>
            <div class="sidebar-section-label">Principal</div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/2_Reservas.py", label="Reservas", icon=":material/event_available:")
        st.page_link("pages/3_Dashboard.py", label="Dashboard", icon=":material/space_dashboard:")

        st.markdown("<div class='sidebar-section-label'>Gestão</div>", unsafe_allow_html=True)
        st.page_link("pages/1_Cadastro.py", label="Nova reserva", icon=":material/add_circle:")
        st.page_link("pages/4_Importar_Excel.py", label="Importar Excel", icon=":material/upload_file:")
        st.page_link("app.py", label="Início", icon=":material/home:")

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
        st.markdown(
            """
            <div class="sidebar-footer">
                <span class="sidebar-footer-dot"></span>
                Sistema conectado
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
    page_code = {
        "Reservas": "R",
        "Dashboard": "D",
        "Cadastro de reserva": "+",
        "Importar Excel": "X",
        "Painel inicial": "H",
    }.get(title, "RH")
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-header-main">
                <div class="app-header-icon">{page_code}</div>
                <div>
                    <div class="app-header-eyebrow">Gestão de hospedagens</div>
                    <h1>{title}</h1>
                    <p>{subtitle or ""}</p>
                </div>
            </div>
            <div class="app-header-status">
                <span class="status-dot"></span>
                Sistema ativo
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

