from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from database import transaction
from services.reserva_service import (
    clear_reserva_caches,
    find_duplicate_cur,
    insert_reserva_cur,
    update_reserva_cur,
)
from utils.formatacao import parse_decimal_br
from utils.validacao import (
    clean_text,
    is_blank,
    normalize_key,
    parse_bool_br,
    parse_date_br,
    parse_int_positive,
    validate_reserva,
)


COLUMN_ALIASES = {
    "data": "data_reserva",
    "datareserva": "data_reserva",
    "dtreserva": "data_reserva",
    "motorista": "motorista",
    "mot": "motorista",
    "ajudante": "ajudante",
    "ajud": "ajudante",
    "cidade": "cidade",
    "municipio": "cidade",
    "hotel": "hotel_pousada",
    "hotelpousada": "hotel_pousada",
    "pousada": "hotel_pousada",
    "hoteloupousada": "hotel_pousada",
    "tipo": "tipo",
    "valor": "valor",
    "vlr": "valor",
    "diarias": "dias",
    "dias": "dias",
    "naoplanejada": "nao_planejada",
    "noplanejada": "nao_planejada",
    "naoplanejado": "nao_planejada",
    "noplanejado": "nao_planejada",
    "naoprogramada": "nao_planejada",
    "noprogramada": "nao_planejada",
    "nplanejada": "nao_planejada",
    "np": "nao_planejada",
    "categoria": "categoria",
    "observacao": "observacao",
    "observacoes": "observacao",
    "obs": "observacao",
}

MIN_HEADER_MATCHES = 3
HEADER_SCAN_ROWS = 40


@dataclass
class ImportPreview:
    records: list[dict[str, Any]]
    errors: list[dict[str, Any]]

    @property
    def valid_count(self) -> int:
        return len(self.records)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def get_sheet_names(uploaded_file: Any) -> list[str]:
    uploaded_file.seek(0)
    excel = pd.ExcelFile(uploaded_file)
    return excel.sheet_names


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for column in df.columns:
        canonical = COLUMN_ALIASES.get(normalize_key(column))
        if canonical and canonical not in used:
            mapping[column] = canonical
            used.add(canonical)
    return df.rename(columns=mapping)


def _canonical_column(value: Any) -> str | None:
    if is_blank(value):
        return None
    return COLUMN_ALIASES.get(normalize_key(value))


def _detect_header_row(raw_df: pd.DataFrame) -> int | None:
    max_rows = min(len(raw_df), HEADER_SCAN_ROWS)
    best_index: int | None = None
    best_score = 0

    for row_index in range(max_rows):
        canonical_columns = {
            canonical
            for canonical in (_canonical_column(value) for value in raw_df.iloc[row_index].tolist())
            if canonical
        }
        score = len(canonical_columns)
        has_required_hint = bool(
            {"data_reserva", "motorista", "cidade", "hotel_pousada"} & canonical_columns
        )
        if score > best_score and has_required_hint:
            best_score = score
            best_index = row_index

    if best_score >= MIN_HEADER_MATCHES:
        return best_index
    return None


def _load_sheet_dataframe(uploaded_file: Any, sheet_name: str) -> tuple[pd.DataFrame, int]:
    uploaded_file.seek(0)
    raw_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=object, header=None)
    header_row = _detect_header_row(raw_df)

    if header_row is None:
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=object)
        return _rename_columns(df), 2

    df = raw_df.iloc[header_row + 1 :].copy()
    df.columns = raw_df.iloc[header_row].tolist()
    df = _rename_columns(df)
    return df, 1


def _row_is_empty(row: pd.Series) -> bool:
    return all(is_blank(value) for value in row.to_dict().values())


def _parse_row(row: pd.Series) -> dict[str, Any]:
    dias = parse_int_positive(row.get("dias"))
    return {
        "data_reserva": parse_date_br(row.get("data_reserva")),
        "motorista": clean_text(row.get("motorista")),
        "ajudante": clean_text(row.get("ajudante")),
        "cidade": clean_text(row.get("cidade")),
        "hotel_pousada": clean_text(row.get("hotel_pousada")),
        "tipo": clean_text(row.get("tipo")),
        "valor": parse_decimal_br(row.get("valor")),
        "dias": dias or 1,
        "nao_planejada": parse_bool_br(row.get("nao_planejada")),
        "categoria": clean_text(row.get("categoria")),
        "observacao": clean_text(row.get("observacao")),
    }


def parse_excel(uploaded_file: Any, sheet_names: list[str]) -> ImportPreview:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for sheet_name in sheet_names:
        df, line_offset = _load_sheet_dataframe(uploaded_file, sheet_name)

        for row_index, row in df.iterrows():
            if _row_is_empty(row):
                continue
            parsed = _parse_row(row)
            excel_line = int(row_index) + line_offset
            parsed["__aba"] = sheet_name
            parsed["__linha"] = excel_line
            row_errors = validate_reserva(parsed)
            if row_errors:
                errors.append(
                    {
                        "aba": sheet_name,
                        "linha": excel_line,
                        "motivo": " ".join(row_errors),
                    }
                )
            else:
                records.append(parsed)

    return ImportPreview(records=records, errors=errors)


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    visible_columns = [
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
        "observacao",
    ]
    return pd.DataFrame(records, columns=visible_columns)


def mark_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    marked: list[dict[str, Any]] = []
    with transaction() as cur:
        for record in records:
            duplicate = find_duplicate_cur(cur, record)
            item = dict(record)
            item["duplicado"] = bool(duplicate)
            item["id_existente"] = duplicate["id"] if duplicate else None
            marked.append(item)
    return marked


def import_records(
    records: list[dict[str, Any]],
    user_id: int | None,
    arquivo: str,
    abas: list[str],
    ignorar_duplicados: bool,
    atualizar_existentes: bool,
) -> dict[str, int]:
    imported = 0
    updated = 0
    ignored = 0

    with transaction() as cur:
        cur.execute(
            """
            INSERT INTO importacoes (arquivo, abas, usuario_id)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (arquivo, ", ".join(abas), user_id),
        )
        importacao_id = int(cur.fetchone()["id"])

        for record in records:
            duplicate = find_duplicate_cur(cur, record)
            if duplicate and atualizar_existentes:
                update_reserva_cur(cur, int(duplicate["id"]), record)
                updated += 1
                continue
            if duplicate and ignorar_duplicados:
                ignored += 1
                continue
            if duplicate:
                raise RuntimeError(
                    f"Duplicidade encontrada na aba {record.get('__aba')} linha {record.get('__linha')}."
                )
            insert_reserva_cur(cur, record, user_id, importacao_id)
            imported += 1

        cur.execute(
            """
            UPDATE importacoes
            SET qtd_importados = %s, qtd_atualizados = %s, qtd_ignorados = %s
            WHERE id = %s
            """,
            (imported, updated, ignored, importacao_id),
        )

    clear_reserva_caches()
    return {"importados": imported, "atualizados": updated, "ignorados": ignored}

