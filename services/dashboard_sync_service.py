from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
import streamlit as st
from psycopg import OperationalError
from psycopg.rows import dict_row

from database import fetch_all, fetch_one, get_setting, transaction


DASHBOARD_SOURCE = "reservas_streamlit"
APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")
AUTOMATIC_SYNC_START_HOUR = 6
AUTOMATIC_SYNC_END_HOUR = 12
_DASHBOARD_SCHEMA_READY = False
_SYNC_RUN_LOCK = threading.Lock()


class DashboardSyncConfigurationError(RuntimeError):
    """Raised when the dashboard Neon connection has not been configured."""


def get_dashboard_database_url() -> str:
    url = get_setting("DASHBOARD_DATABASE_URL")
    if not url:
        raise DashboardSyncConfigurationError(
            "DASHBOARD_DATABASE_URL nao configurada para sincronizar com o dashboard."
        )
    return url


@st.cache_resource(show_spinner=False)
def _dashboard_connection(database_url: str) -> psycopg.Connection:
    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=5,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


@st.cache_resource(show_spinner=False)
def _dashboard_lock() -> threading.RLock:
    return threading.RLock()


def _discard_dashboard_connection(conn: psycopg.Connection | None = None) -> None:
    try:
        if conn is not None and not conn.closed:
            conn.close()
    except Exception:
        pass
    _dashboard_connection.clear()


def _get_dashboard_connection() -> psycopg.Connection:
    conn = _dashboard_connection(get_dashboard_database_url())
    if conn.closed:
        _discard_dashboard_connection(conn)
        conn = _dashboard_connection(get_dashboard_database_url())
    return conn


def _ensure_dashboard_schema(cur: psycopg.Cursor) -> None:
    global _DASHBOARD_SCHEMA_READY
    if _DASHBOARD_SCHEMA_READY:
        return
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS dashboard_hoteis (
            "__jr_schema_marker" TEXT
        )
        '''
    )
    columns = {
        "Data": "TIMESTAMP",
        "Valor": "DOUBLE PRECISION",
        "Dias": "DOUBLE PRECISION",
        "Mes": "TEXT",
        "Motorista": "TEXT",
        "Ajudante": "TEXT",
        "Cidade": "TEXT",
        "Hotel": "TEXT",
        "Tipo": "TEXT",
        "Categoria": "TEXT",
        "Reserva ID": "UUID",
        "Reserva Origem ID": "BIGINT",
        "Nao Planejada": "BOOLEAN",
        "Observacao": "TEXT",
        "Origem": "TEXT",
        "Atualizado Em": "TIMESTAMPTZ",
    }
    for name, sql_type in columns.items():
        escaped_name = name.replace('"', '""')
        cur.execute(
            f'ALTER TABLE dashboard_hoteis ADD COLUMN IF NOT EXISTS "{escaped_name}" {sql_type}'
        )
    cur.execute(
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_hoteis_reserva_id
        ON dashboard_hoteis ("Reserva ID")
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS dashboard_metadata (
            "key" TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )


def _write_dashboard_version(cur: psycopg.Cursor) -> None:
    version = datetime.now(timezone.utc).isoformat()
    for key in ("hoteis.version", "import.version"):
        cur.execute(
            '''
            INSERT INTO dashboard_metadata ("key", value_json, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT ("key")
            DO UPDATE SET value_json = EXCLUDED.value_json,
                          updated_at = CURRENT_TIMESTAMP
            ''',
            (key, f'"{version}"'),
        )


def _upsert_dashboard_reserva(reserva: dict[str, Any]) -> None:
    global _DASHBOARD_SCHEMA_READY
    month = reserva["data_reserva"].strftime("%Y-%m") if reserva.get("data_reserva") else None
    params = {
        "data": reserva.get("data_reserva"),
        "valor": reserva.get("valor"),
        "dias": reserva.get("dias"),
        "mes": month,
        "motorista": reserva.get("motorista") or None,
        "ajudante": reserva.get("ajudante") or None,
        "cidade": reserva.get("cidade") or None,
        "hotel": reserva.get("hotel_pousada") or None,
        "tipo": reserva.get("tipo") or None,
        "categoria": reserva.get("categoria") or None,
        "reserva_id": reserva["sync_id"],
        "reserva_origem_id": reserva["id"],
        "nao_planejada": bool(reserva.get("nao_planejada")),
        "observacao": reserva.get("observacao") or None,
        "origem": DASHBOARD_SOURCE,
        "atualizado_em": reserva["atualizado_em"],
    }

    for attempt in range(2):
        conn: psycopg.Connection | None = None
        try:
            with _dashboard_lock():
                conn = _get_dashboard_connection()
                with conn.cursor() as cur:
                    _ensure_dashboard_schema(cur)
                    cur.execute(
                        '''
                        INSERT INTO dashboard_hoteis (
                            "Data", "Valor", "Dias", "Mes", "Motorista", "Ajudante",
                            "Cidade", "Hotel", "Tipo", "Categoria", "Reserva ID",
                            "Reserva Origem ID", "Nao Planejada", "Observacao", "Origem",
                            "Atualizado Em"
                        )
                        VALUES (
                            %(data)s, %(valor)s, %(dias)s, %(mes)s, %(motorista)s, %(ajudante)s,
                            %(cidade)s, %(hotel)s, %(tipo)s, %(categoria)s, %(reserva_id)s,
                            %(reserva_origem_id)s, %(nao_planejada)s, %(observacao)s, %(origem)s,
                            %(atualizado_em)s
                        )
                        ON CONFLICT ("Reserva ID") DO UPDATE SET
                            "Data" = EXCLUDED."Data",
                            "Valor" = EXCLUDED."Valor",
                            "Dias" = EXCLUDED."Dias",
                            "Mes" = EXCLUDED."Mes",
                            "Motorista" = EXCLUDED."Motorista",
                            "Ajudante" = EXCLUDED."Ajudante",
                            "Cidade" = EXCLUDED."Cidade",
                            "Hotel" = EXCLUDED."Hotel",
                            "Tipo" = EXCLUDED."Tipo",
                            "Categoria" = EXCLUDED."Categoria",
                            "Reserva Origem ID" = EXCLUDED."Reserva Origem ID",
                            "Nao Planejada" = EXCLUDED."Nao Planejada",
                            "Observacao" = EXCLUDED."Observacao",
                            "Origem" = EXCLUDED."Origem",
                            "Atualizado Em" = EXCLUDED."Atualizado Em"
                        WHERE dashboard_hoteis."Atualizado Em" IS NULL
                           OR EXCLUDED."Atualizado Em" >= dashboard_hoteis."Atualizado Em"
                        ''',
                        params,
                    )
                    _write_dashboard_version(cur)
                conn.commit()
                _DASHBOARD_SCHEMA_READY = True
            return
        except OperationalError:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
                _discard_dashboard_connection(conn)
            if attempt == 1:
                raise
        except Exception:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    _discard_dashboard_connection(conn)
            raise


def _load_syncable_reserva(reserva_id: int) -> dict[str, Any] | None:
    return fetch_one(
        '''
        SELECT id, sync_id, data_reserva, motorista, ajudante, cidade,
               hotel_pousada, tipo, valor, dias, nao_planejada, categoria,
               observacao, atualizado_em
        FROM reservas_hotel
        WHERE id = %s AND sincronizar_dashboard = TRUE
        ''',
        (reserva_id,),
    )


def _mark_sync_success(reserva: dict[str, Any]) -> None:
    with transaction() as cur:
        cur.execute(
            '''
            INSERT INTO reservas_dashboard_sync (
                reserva_id, source_atualizado_em, sincronizado_em, ultimo_erro
            )
            VALUES (%s, %s, NOW(), NULL)
            ON CONFLICT (reserva_id) DO UPDATE SET
                source_atualizado_em = EXCLUDED.source_atualizado_em,
                sincronizado_em = NOW(),
                ultimo_erro = NULL
            ''',
            (reserva["id"], reserva["atualizado_em"]),
        )


def _mark_sync_error(reserva_id: int, error: Exception) -> None:
    message = str(error).strip()[:2000] or error.__class__.__name__
    with transaction() as cur:
        cur.execute(
            '''
            INSERT INTO reservas_dashboard_sync (reserva_id, ultimo_erro)
            VALUES (%s, %s)
            ON CONFLICT (reserva_id) DO UPDATE SET ultimo_erro = EXCLUDED.ultimo_erro
            ''',
            (reserva_id, message),
        )


def sync_reserva(reserva_id: int) -> bool:
    reserva = _load_syncable_reserva(reserva_id)
    if not reserva:
        return False
    try:
        _upsert_dashboard_reserva(reserva)
        _mark_sync_success(reserva)
        return True
    except Exception as exc:
        _mark_sync_error(reserva_id, exc)
        raise


def try_sync_reserva(reserva_id: int) -> bool:
    try:
        return sync_reserva(reserva_id)
    except Exception:
        # A reserva ja foi confirmada no banco principal. Ela permanece pendente
        # e sera reenviada sem induzir o usuario a duplicar o cadastro.
        return False


def sync_pending_reservas(limit: int = 100) -> dict[str, int]:
    pending = fetch_all(
        '''
        SELECT r.id
        FROM reservas_hotel r
        LEFT JOIN reservas_dashboard_sync s ON s.reserva_id = r.id
        WHERE r.sincronizar_dashboard = TRUE
          AND s.source_atualizado_em IS DISTINCT FROM r.atualizado_em
        ORDER BY r.atualizado_em, r.id
        LIMIT %s
        ''',
        (max(1, min(int(limit), 500)),),
    )
    synced = 0
    for item in pending:
        try:
            sync_reserva(int(item["id"]))
            synced += 1
        except Exception:
            # Uma indisponibilidade do destino afetaria todo o lote. Interromper
            # aqui evita dezenas de timeouts e deixa todos os itens para o retry.
            break
    failed = len(pending) - synced
    return {"pendentes": len(pending), "sincronizadas": synced, "falhas": failed}


def _pending_count() -> int:
    row = fetch_one(
        '''
        SELECT COUNT(*)::INT AS quantidade
        FROM reservas_hotel r
        LEFT JOIN reservas_dashboard_sync s ON s.reserva_id = r.id
        WHERE r.sincronizar_dashboard = TRUE
          AND s.source_atualizado_em IS DISTINCT FROM r.atualizado_em
        '''
    )
    return int(row["quantidade"] if row else 0)


def sync_all_pending(max_records: int = 5000) -> dict[str, int | bool]:
    if not _SYNC_RUN_LOCK.acquire(blocking=False):
        return {
            "sincronizadas": 0,
            "falhas": 0,
            "pendentes": 0,
            "em_andamento": True,
        }

    synced = 0
    failures = 0
    try:
        while synced < max_records:
            batch_size = min(500, max_records - synced)
            result = sync_pending_reservas(limit=batch_size)
            synced += int(result["sincronizadas"])
            if result["falhas"]:
                failures = int(result["falhas"])
                break
            if result["pendentes"] < batch_size:
                break
        return {
            "sincronizadas": synced,
            "falhas": failures,
            "pendentes": _pending_count(),
            "em_andamento": False,
        }
    finally:
        _SYNC_RUN_LOCK.release()


def get_scheduled_sync_status(reference: datetime | None = None) -> dict[str, Any] | None:
    current = reference or datetime.now(APP_TIMEZONE)
    return fetch_one(
        '''
        SELECT data_execucao, status, iniciado_em, concluido_em,
               qtd_sincronizadas, qtd_pendentes, mensagem
        FROM reservas_dashboard_execucoes_diarias
        WHERE data_execucao = %s
        ''',
        (current.date(),),
    )


def mark_manual_sync_success(
    result: dict[str, int | bool],
    reference: datetime | None = None,
) -> None:
    current = reference or datetime.now(APP_TIMEZONE)
    with transaction() as cur:
        cur.execute(
            '''
            INSERT INTO reservas_dashboard_execucoes_diarias (
                data_execucao, status, iniciado_em, concluido_em,
                qtd_sincronizadas, qtd_pendentes, mensagem
            )
            VALUES (%s, 'concluido', NOW(), NOW(), %s, 0, %s)
            ON CONFLICT (data_execucao) DO UPDATE SET
                status = 'concluido',
                concluido_em = NOW(),
                qtd_sincronizadas = EXCLUDED.qtd_sincronizadas,
                qtd_pendentes = 0,
                mensagem = EXCLUDED.mensagem
            ''',
            (
                current.date(),
                int(result["sincronizadas"]),
                "Envio manual concluido corretamente.",
            ),
        )


def run_scheduled_sync_if_due(reference: datetime | None = None) -> dict[str, Any]:
    current = reference or datetime.now(APP_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=APP_TIMEZONE)
    if not AUTOMATIC_SYNC_START_HOUR <= current.hour < AUTOMATIC_SYNC_END_HOUR:
        return {"executada": False, "motivo": "fora_do_horario"}

    with transaction() as cur:
        cur.execute(
            '''
            INSERT INTO reservas_dashboard_execucoes_diarias (
                data_execucao, status, iniciado_em, qtd_sincronizadas, qtd_pendentes
            )
            VALUES (%s, 'executando', NOW(), 0, 0)
            ON CONFLICT (data_execucao) DO NOTHING
            RETURNING data_execucao
            ''',
            (current.date(),),
        )
        claimed = cur.fetchone()

    if not claimed:
        return {
            "executada": False,
            "motivo": "ja_executada",
            "status": get_scheduled_sync_status(current),
        }

    result = sync_all_pending()
    if result.get("em_andamento"):
        status = "erro"
        message = "Ja existe outro envio em andamento."
    elif result["falhas"] or result["pendentes"]:
        status = "erro"
        message = "O envio nao foi concluido; os dados permanecem pendentes."
    else:
        status = "concluido"
        message = "Dados enviados corretamente ao dashboard."

    with transaction() as cur:
        cur.execute(
            '''
            UPDATE reservas_dashboard_execucoes_diarias
            SET status = %s,
                concluido_em = NOW(),
                qtd_sincronizadas = %s,
                qtd_pendentes = %s,
                mensagem = %s
            WHERE data_execucao = %s
            ''',
            (
                status,
                int(result["sincronizadas"]),
                int(result["pendentes"]),
                message,
                current.date(),
            ),
        )
    return {"executada": True, "status": status, **result}
