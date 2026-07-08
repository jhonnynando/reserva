from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from utils.formatacao import parse_decimal_br


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def clean_text(value: Any) -> str:
    if is_blank(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def parse_bool_br(value: Any) -> bool:
    if is_blank(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    text = clean_text(value).lower()
    if text in {"1", "sim", "s", "true", "t", "x", "yes", "y"}:
        return True
    if text in {"0", "nao", "não", "n", "false", "f", "no"}:
        return False
    return True


def parse_date_br(value: Any) -> date | None:
    if is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        import pandas as pd

        parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def parse_int_positive(value: Any) -> int | None:
    if is_blank(value):
        return None
    try:
        number = int(float(str(value).replace(",", ".")))
    except ValueError:
        return None
    return number if number > 0 else None


def validate_reserva(data: dict[str, Any], strict: bool = True) -> list[str]:
    errors: list[str] = []
    if not data.get("data_reserva"):
        errors.append("Data obrigatória.")
    if strict:
        if not clean_text(data.get("motorista")):
            errors.append("Motorista obrigatório.")
        if not clean_text(data.get("cidade")):
            errors.append("Cidade obrigatória.")
        if not clean_text(data.get("hotel_pousada")):
            errors.append("Hotel/Pousada obrigatório.")

    valor = data.get("valor")
    if not isinstance(valor, Decimal):
        valor = parse_decimal_br(valor)
    if strict and (valor is None or valor <= 0):
        errors.append("Valor deve ser maior que zero.")

    dias = data.get("dias")
    if dias is None or int(dias) <= 0:
        errors.append("Dias deve ser maior que zero.")
    return errors

