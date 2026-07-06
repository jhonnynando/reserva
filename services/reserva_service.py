from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from database import execute, execute_returning, fetch_all, fetch_one, transaction
from utils.validacao import clean_text


class DuplicateReservationError(RuntimeError):
    def __init__(self, duplicate: dict[str, Any]) -> None:
        super().__init__("Possível reserva duplicada.")
        self.duplicate = duplicate


def list_motoristas(active_only: bool = True, search: str = "") -> list[dict[str, Any]]:
    where = ["1=1"]
    params: list[Any] = []
    if active_only:
        where.append("ativo = TRUE")
    if search:
        where.append("nome ILIKE %s")
        params.append(f"%{search}%")
    return fetch_all(
        f"SELECT id, nome, ativo FROM motoristas WHERE {' AND '.join(where)} ORDER BY nome",
        params,
    )


def list_ajudantes(active_only: bool = True, search: str = "") -> list[dict[str, Any]]:
    where = ["1=1"]
    params: list[Any] = []
    if active_only:
        where.append("ativo = TRUE")
    if search:
        where.append("nome ILIKE %s")
        params.append(f"%{search}%")
    return fetch_all(
        f"SELECT id, nome, ativo FROM ajudantes WHERE {' AND '.join(where)} ORDER BY nome",
        params,
    )


def list_cidades(active_only: bool = True, search: str = "") -> list[dict[str, Any]]:
    where = ["1=1"]
    params: list[Any] = []
    if active_only:
        where.append("ativo = TRUE")
    if search:
        where.append("(nome ILIKE %s OR estado ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    return fetch_all(
        f"""
        SELECT id, nome, estado, ativo
        FROM cidades
        WHERE {' AND '.join(where)}
        ORDER BY nome, estado
        """,
        params,
    )


def list_hoteis(
    cidade_id: int | None = None,
    active_only: bool = True,
    search: str = "",
) -> list[dict[str, Any]]:
    where = ["1=1"]
    params: list[Any] = []
    if active_only:
        where.append("h.ativo = TRUE")
    if cidade_id:
        where.append("h.cidade_id = %s")
        params.append(cidade_id)
    if search:
        where.append("(h.nome ILIKE %s OR c.nome ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    return fetch_all(
        f"""
        SELECT h.id, h.nome, h.cidade_id, c.nome AS cidade, c.estado,
               h.telefone, h.observacao, h.ativo
        FROM hoteis h
        LEFT JOIN cidades c ON c.id = h.cidade_id
        WHERE {' AND '.join(where)}
        ORDER BY c.nome NULLS LAST, h.nome
        """,
        params,
    )


def _find_by_name(cur: Any, table: str, nome: str) -> dict[str, Any] | None:
    cur.execute(f"SELECT id, nome, ativo FROM {table} WHERE LOWER(nome) = LOWER(%s) LIMIT 1", (nome,))
    return cur.fetchone()


def upsert_motorista_cur(cur: Any, nome: str) -> int | None:
    nome = clean_text(nome)
    if not nome:
        return None
    existing = _find_by_name(cur, "motoristas", nome)
    if existing:
        return int(existing["id"])
    cur.execute("INSERT INTO motoristas (nome, ativo) VALUES (%s, TRUE) RETURNING id", (nome,))
    return int(cur.fetchone()["id"])


def upsert_ajudante_cur(cur: Any, nome: str) -> int | None:
    nome = clean_text(nome)
    if not nome:
        return None
    existing = _find_by_name(cur, "ajudantes", nome)
    if existing:
        return int(existing["id"])
    cur.execute("INSERT INTO ajudantes (nome, ativo) VALUES (%s, TRUE) RETURNING id", (nome,))
    return int(cur.fetchone()["id"])


def upsert_cidade_cur(cur: Any, nome: str, estado: str | None = None) -> int | None:
    nome = clean_text(nome)
    estado = clean_text(estado).upper()[:2] or None
    if not nome:
        return None
    cur.execute(
        """
        SELECT id, nome, estado
        FROM cidades
        WHERE LOWER(nome) = LOWER(%s)
          AND COALESCE(estado, '') = COALESCE(%s, COALESCE(estado, ''))
        LIMIT 1
        """,
        (nome, estado),
    )
    existing = cur.fetchone()
    if existing:
        return int(existing["id"])
    cur.execute(
        "INSERT INTO cidades (nome, estado, ativo) VALUES (%s, %s, TRUE) RETURNING id",
        (nome, estado),
    )
    return int(cur.fetchone()["id"])


def upsert_hotel_cur(cur: Any, nome: str, cidade_id: int | None = None) -> int | None:
    nome = clean_text(nome)
    if not nome:
        return None
    cur.execute(
        """
        SELECT id
        FROM hoteis
        WHERE LOWER(nome) = LOWER(%s)
          AND COALESCE(cidade_id, 0) = COALESCE(%s, COALESCE(cidade_id, 0))
        LIMIT 1
        """,
        (nome, cidade_id),
    )
    existing = cur.fetchone()
    if existing:
        return int(existing["id"])
    cur.execute(
        "INSERT INTO hoteis (nome, cidade_id, ativo) VALUES (%s, %s, TRUE) RETURNING id",
        (nome, cidade_id),
    )
    return int(cur.fetchone()["id"])


def ensure_auxiliares_para_reserva_cur(cur: Any, data: dict[str, Any]) -> None:
    upsert_motorista_cur(cur, data.get("motorista", ""))
    upsert_ajudante_cur(cur, data.get("ajudante", ""))
    cidade_id = upsert_cidade_cur(cur, data.get("cidade", ""))
    upsert_hotel_cur(cur, data.get("hotel_pousada", ""), cidade_id)


def add_motorista(nome: str) -> int:
    with transaction() as cur:
        return int(upsert_motorista_cur(cur, nome))


def add_ajudante(nome: str) -> int:
    with transaction() as cur:
        return int(upsert_ajudante_cur(cur, nome))


def add_cidade(nome: str, estado: str | None = None) -> int:
    with transaction() as cur:
        return int(upsert_cidade_cur(cur, nome, estado))


def add_hotel(nome: str, cidade_id: int | None, telefone: str = "", observacao: str = "") -> int:
    with transaction() as cur:
        hotel_id = upsert_hotel_cur(cur, nome, cidade_id)
        cur.execute(
            """
            UPDATE hoteis
            SET telefone = COALESCE(NULLIF(%s, ''), telefone),
                observacao = COALESCE(NULLIF(%s, ''), observacao)
            WHERE id = %s
            """,
            (clean_text(telefone), clean_text(observacao), hotel_id),
        )
        return int(hotel_id)


def update_motorista(item_id: int, nome: str, ativo: bool) -> None:
    execute("UPDATE motoristas SET nome = %s, ativo = %s WHERE id = %s", (clean_text(nome), ativo, item_id))


def update_ajudante(item_id: int, nome: str, ativo: bool) -> None:
    execute("UPDATE ajudantes SET nome = %s, ativo = %s WHERE id = %s", (clean_text(nome), ativo, item_id))


def update_cidade(item_id: int, nome: str, estado: str | None, ativo: bool) -> None:
    execute(
        "UPDATE cidades SET nome = %s, estado = %s, ativo = %s WHERE id = %s",
        (clean_text(nome), clean_text(estado).upper()[:2] or None, ativo, item_id),
    )


def update_hotel(
    item_id: int,
    nome: str,
    cidade_id: int | None,
    telefone: str,
    observacao: str,
    ativo: bool,
) -> None:
    execute(
        """
        UPDATE hoteis
        SET nome = %s, cidade_id = %s, telefone = %s, observacao = %s, ativo = %s
        WHERE id = %s
        """,
        (clean_text(nome), cidade_id, clean_text(telefone), clean_text(observacao), ativo, item_id),
    )


def find_duplicate_cur(cur: Any, data: dict[str, Any], ignore_id: int | None = None) -> dict[str, Any] | None:
    params: list[Any] = [
        data["data_reserva"],
        clean_text(data["motorista"]),
        clean_text(data["cidade"]),
        clean_text(data["hotel_pousada"]),
        data["valor"],
    ]
    id_clause = ""
    if ignore_id:
        id_clause = "AND id <> %s"
        params.append(ignore_id)
    cur.execute(
        f"""
        SELECT *
        FROM reservas_hotel
        WHERE data_reserva = %s
          AND LOWER(motorista) = LOWER(%s)
          AND LOWER(cidade) = LOWER(%s)
          AND LOWER(hotel_pousada) = LOWER(%s)
          AND valor = %s
          {id_clause}
        ORDER BY id
        LIMIT 1
        """,
        params,
    )
    return cur.fetchone()


def find_duplicate(data: dict[str, Any], ignore_id: int | None = None) -> dict[str, Any] | None:
    with transaction() as cur:
        return find_duplicate_cur(cur, data, ignore_id)


def insert_reserva_cur(
    cur: Any,
    data: dict[str, Any],
    user_id: int | None,
    importacao_id: int | None = None,
) -> int:
    ensure_auxiliares_para_reserva_cur(cur, data)
    cur.execute(
        """
        INSERT INTO reservas_hotel (
            data_reserva, motorista, ajudante, cidade, hotel_pousada, tipo,
            valor, dias, nao_planejada, categoria, observacao, criado_por, importacao_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            data["data_reserva"],
            clean_text(data["motorista"]),
            clean_text(data.get("ajudante")),
            clean_text(data["cidade"]),
            clean_text(data["hotel_pousada"]),
            clean_text(data.get("tipo")),
            data["valor"],
            data["dias"],
            bool(data.get("nao_planejada")),
            clean_text(data.get("categoria")),
            clean_text(data.get("observacao")),
            user_id,
            importacao_id,
        ),
    )
    return int(cur.fetchone()["id"])


def update_reserva_cur(cur: Any, reserva_id: int, data: dict[str, Any]) -> None:
    ensure_auxiliares_para_reserva_cur(cur, data)
    cur.execute(
        """
        UPDATE reservas_hotel
        SET data_reserva = %s,
            motorista = %s,
            ajudante = %s,
            cidade = %s,
            hotel_pousada = %s,
            tipo = %s,
            valor = %s,
            dias = %s,
            nao_planejada = %s,
            categoria = %s,
            observacao = %s
        WHERE id = %s
        """,
        (
            data["data_reserva"],
            clean_text(data["motorista"]),
            clean_text(data.get("ajudante")),
            clean_text(data["cidade"]),
            clean_text(data["hotel_pousada"]),
            clean_text(data.get("tipo")),
            data["valor"],
            data["dias"],
            bool(data.get("nao_planejada")),
            clean_text(data.get("categoria")),
            clean_text(data.get("observacao")),
            reserva_id,
        ),
    )


def create_reserva(data: dict[str, Any], user_id: int | None, allow_duplicate: bool = False) -> int:
    with transaction() as cur:
        duplicate = find_duplicate_cur(cur, data)
        if duplicate and not allow_duplicate:
            raise DuplicateReservationError(duplicate)
        return insert_reserva_cur(cur, data, user_id)


def update_reserva(reserva_id: int, data: dict[str, Any], allow_duplicate: bool = False) -> None:
    with transaction() as cur:
        duplicate = find_duplicate_cur(cur, data, ignore_id=reserva_id)
        if duplicate and not allow_duplicate:
            raise DuplicateReservationError(duplicate)
        update_reserva_cur(cur, reserva_id, data)


def delete_reserva(reserva_id: int) -> None:
    execute("DELETE FROM reservas_hotel WHERE id = %s", (reserva_id,))


def get_reserva(reserva_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM reservas_hotel WHERE id = %s", (reserva_id,))


def _add_filter(where: list[str], params: list[Any], clause: str, *values: Any) -> None:
    where.append(clause)
    params.extend(values)


def build_filter_sql(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    where = ["1=1"]
    params: list[Any] = []
    if filters.get("data_inicio"):
        _add_filter(where, params, "data_reserva >= %s", filters["data_inicio"])
    if filters.get("data_fim"):
        _add_filter(where, params, "data_reserva <= %s", filters["data_fim"])
    if filters.get("ano"):
        _add_filter(where, params, "EXTRACT(YEAR FROM data_reserva) = %s", filters["ano"])
    if filters.get("mes"):
        _add_filter(where, params, "EXTRACT(MONTH FROM data_reserva) = %s", filters["mes"])
    if filters.get("dia"):
        _add_filter(where, params, "EXTRACT(DAY FROM data_reserva) = %s", filters["dia"])
    for field in ("motorista", "ajudante", "cidade", "hotel_pousada", "tipo", "categoria"):
        if filters.get(field):
            _add_filter(where, params, f"{field} = %s", filters[field])
    if filters.get("nao_planejada") is not None:
        _add_filter(where, params, "nao_planejada = %s", filters["nao_planejada"])
    if filters.get("valor_min") is not None:
        _add_filter(where, params, "valor >= %s", filters["valor_min"])
    if filters.get("valor_max") is not None:
        _add_filter(where, params, "valor <= %s", filters["valor_max"])
    if filters.get("busca"):
        busca = f"%{filters['busca']}%"
        _add_filter(
            where,
            params,
            """
            (
                motorista ILIKE %s OR ajudante ILIKE %s OR cidade ILIKE %s OR
                hotel_pousada ILIKE %s OR tipo ILIKE %s OR categoria ILIKE %s OR
                observacao ILIKE %s OR TO_CHAR(data_reserva, 'DD/MM/YYYY') ILIKE %s
            )
            """,
            busca,
            busca,
            busca,
            busca,
            busca,
            busca,
            busca,
            busca,
        )
    return " AND ".join(where), params


def list_reservas(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    filters = filters or {}
    where_sql, params = build_filter_sql(filters)
    return fetch_all(
        f"""
        SELECT id, data_reserva, motorista, ajudante, cidade, hotel_pousada, tipo,
               valor, dias, nao_planejada, categoria, observacao, criado_por,
               criado_em, atualizado_em
        FROM reservas_hotel
        WHERE {where_sql}
        ORDER BY data_reserva DESC, id DESC
        """,
        params,
    )


def distinct_values(field: str) -> list[str]:
    allowed = {"motorista", "ajudante", "cidade", "hotel_pousada", "tipo", "categoria"}
    if field not in allowed:
        raise ValueError("Campo de filtro inválido.")
    rows = fetch_all(
        f"""
        SELECT DISTINCT {field} AS value
        FROM reservas_hotel
        WHERE {field} IS NOT NULL AND TRIM({field}) <> ''
        ORDER BY {field}
        """
    )
    return [row["value"] for row in rows]


def available_years() -> list[int]:
    rows = fetch_all(
        """
        SELECT DISTINCT EXTRACT(YEAR FROM data_reserva)::INT AS ano
        FROM reservas_hotel
        ORDER BY ano DESC
        """
    )
    return [int(row["ano"]) for row in rows]

