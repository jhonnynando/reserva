from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math
from typing import Any


def parse_decimal_br(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, Decimal):
        if value.is_nan():
            return None
        return value.quantize(Decimal("0.01"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            decimal_value = Decimal(str(value))
            if decimal_value.is_nan():
                return None
            return decimal_value.quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None
    text = text.replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def format_currency_br(value: Any) -> str:
    decimal_value = parse_decimal_br(value) or Decimal("0.00")
    formatted = f"{decimal_value:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_decimal_br(value: Any, places: int = 2) -> str:
    decimal_value = parse_decimal_br(value) or Decimal("0.00")
    formatted = f"{decimal_value:,.{places}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_date_br(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.strftime("%d/%m/%Y")
    except ValueError:
        return str(value)

