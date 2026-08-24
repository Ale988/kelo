from __future__ import annotations

import re

_MONEY_RE = re.compile(
    r"(?<!\d)(-?\d{1,3}(?:\.\d{3})*(?:,\d{2})|-?\d+,\d{2}|-?\d+)(?:\s*€)?"
)
# Line importi like "8,54 €" exclude unit prices ("0,19 €/kWh", "7,92 €/mese").
_EURO_IMPORTO_RE = re.compile(
    r"(?<!\d)(-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2})\s*€(?!\s*/)"
)
_DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def parse_money(text: str) -> float | None:
    if not text:
        return None
    m = _MONEY_RE.search(text.replace("\xa0", " "))
    if not m:
        return None
    return _to_float(m.group(1))


def parse_last_euro_importo(text: str) -> float | None:
    """Prefer the rightmost euro importo on a line/block (not qty or €/unit)."""
    if not text:
        return None
    matches = list(_EURO_IMPORTO_RE.finditer(text.replace("\xa0", " ")))
    if not matches:
        return None
    return _to_float(matches[-1].group(1))


def parse_first_euro_importo(text: str) -> float | None:
    """First euro importo on a line (label total before ``di cui`` breakdowns)."""
    if not text:
        return None
    m = _EURO_IMPORTO_RE.search(text.replace("\xa0", " "))
    if not m:
        return None
    return _to_float(m.group(1))


def parse_italian_date(text: str) -> str | None:
    if not text:
        return None
    m = _DATE_RE.search(text)
    if not m:
        return None
    d, mo, y = m.group(1), m.group(2), m.group(3)
    return f"{y}-{mo}-{d}"
