from __future__ import annotations

import re

from parsers.money import (
    parse_first_euro_importo,
    parse_italian_date,
    parse_last_euro_importo,
    parse_money,
)
from parsers.schema import (
    BillMvp,
    Consumo,
    PuntoFornitura,
    Subtotali,
    finalize,
)

_FORNITORI = (
    "Octopus Energy",
    "Octopus",
    "NeN",
    "YADA Energia",
    "YADA",
    "Enel",
    "Eni Plenitude",
    "Eni",
    "A2A",
    "Hera",
    "Edison",
)

_TOTALE_LABELS = (
    r"TOTALE\s+DA\s+PAGARE",
    r"Totale\s+da\s+[Pp]agare",
    r"TOTALE\s+BOLLETTA",
    r"Totale\s+Bolletta",
)

_SUBTOTAL_PATTERNS: list[tuple[str, str]] = [
    ("quota_consumi", r"Quota\s+per\s+consumi"),
    ("quota_fissa", r"Quota\s+fissa"),
    ("quota_potenza", r"Quota\s+potenza"),
    ("ricalcoli", r"(?:Totale\s+)?Ricalcoli"),
    ("accise_iva", r"Accise\s+e\s+IVA"),
]

# Summed into altre_partite (NeN cuscinetto, Octopus bonus/credito, …).
_ALTRE_PARTITE_LABELS = (
    r"Altre\s+partite",
    r"Bonus\s+applicati",
    r"Credito\s+rimanente",
)


# Italian POD is typically 14 chars: IT + 3 digits + letter + 8 alphanumerics.
_POD_CODE = r"IT\d{3}[A-Z][A-Z0-9]{8}"


def detect_servizio(text: str) -> str | None:
    lower = text.lower()
    ele_score = 0
    gas_score = 0

    if re.search(r"\bPOD\b", text) or re.search(rf"\b{_POD_CODE}\b", text):
        ele_score += 2
    if re.search(r"\bkWh\b", text, re.I):
        ele_score += 2
    if re.search(r"BOLLETTA\s+LUCE", text, re.I):
        ele_score += 3
    if "energia elettrica" in lower:
        ele_score += 2

    if re.search(r"\bPDR\b", text):
        gas_score += 2
    if re.search(r"\bSmc\b", text):
        gas_score += 2
    if "gas naturale" in lower or re.search(r"\bgas\b", lower):
        gas_score += 1
    if re.search(r"offerta\s+attiva:\s*gas", lower):
        gas_score += 2

    if ele_score == 0 and gas_score == 0:
        return None
    if ele_score > gas_score:
        return "elettrico"
    if gas_score > ele_score:
        return "gas"
    return None


def _money_after(text: str, start: int, window: int = 400) -> float | None:
    """Amount after a label: same line first, else next non-empty line(s).

    - Same line as the label: **first** euro importo (avoids ``di cui … 12,68 €``
      after ``Ricalcoli … -4,76 €``).
    - Following detail lines: **last** euro importo so
      ``45 kWh x 0,19 €/kWh … 8,54 €`` yields 8.54, not 45.
    Only ``X,XX €`` importi count — bare quantities (``45 kWh``) are skipped.
  """
    nl = text.find("\n", start)
    line_end = len(text) if nl < 0 else nl
    same_line = text[start:line_end]
    amount = parse_first_euro_importo(same_line)
    if amount is not None:
        return amount

    cursor = line_end + 1 if nl >= 0 else len(text)
    limit = min(len(text), start + window)
    non_empty_seen = 0
    while cursor < limit and non_empty_seen < 6:
        next_nl = text.find("\n", cursor)
        end = limit if next_nl < 0 or next_nl > limit else next_nl
        line = text[cursor:end]
        if line.strip():
            non_empty_seen += 1
            amount = parse_last_euro_importo(line)
            if amount is not None:
                return amount
        if next_nl < 0 or next_nl >= limit:
            break
        cursor = next_nl + 1

    return parse_first_euro_importo(same_line)


def extract_totale(text: str) -> float | None:
    for label in _TOTALE_LABELS:
        for m in re.finditer(label, text, re.I):
            amount = _money_after(text, m.end())
            if amount is not None:
                return amount
    return None


def extract_scadenza(text: str) -> str | None:
    m = re.search(r"[Ee]ntro\s+il\s+(\d{2}/\d{2}/\d{4})", text)
    if not m:
        return None
    return parse_italian_date(m.group(1))


def extract_periodo(text: str) -> dict[str, str | None]:
    empty: dict[str, str | None] = {"dal": None, "al": None}
    m = re.search(
        r"(?:PERIODO(?:\s+DI\s+RIFERIMENTO)?|Periodo\s+di\s+riferimento)"
        r"[\s:]*"
        r"(?:dal\s+)?(\d{2}/\d{2}/\d{4})\s*(?:al|-)\s*(\d{2}/\d{2}/\d{4})",
        text,
        re.I,
    )
    if m:
        return {
            "dal": parse_italian_date(m.group(1)),
            "al": parse_italian_date(m.group(2)),
        }
    # Dates on following lines after Periodo di riferimento
    m2 = re.search(
        r"(?:PERIODO(?:\s+DI\s+RIFERIMENTO)?|Periodo\s+di\s+riferimento)"
        r"[\s\S]{0,60}?"
        r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
        text,
        re.I,
    )
    if m2:
        return {
            "dal": parse_italian_date(m2.group(1)),
            "al": parse_italian_date(m2.group(2)),
        }
    return empty


def extract_consumo(text: str) -> Consumo:
    m = re.search(r"CONSUMO\s+FATTURATO:\s*([\d.,]+)\s*kWh", text, re.I)
    if m:
        return Consumo(valore=parse_money(m.group(1)), unita="kWh")

    m = re.search(
        r"Consumo\s+totale\s+fatturato[\s\S]{0,80}?([\d.,]+)\s*Smc",
        text,
        re.I,
    )
    if m:
        return Consumo(valore=parse_money(m.group(1)), unita="Smc")

    return Consumo()


def extract_punto(text: str) -> PuntoFornitura:
    m = re.search(
        rf"CODICE\s+POD[\s:]*\n?\s*({_POD_CODE})",
        text,
        re.I,
    )
    if m:
        return PuntoFornitura(tipo="POD", codice=m.group(1).upper())

    # Label may share the line with other headers; code is often on the next line.
    m = re.search(r"\bPDR\b[^\n]*\n\s*(\d{8,})", text, re.I)
    if m:
        return PuntoFornitura(tipo="PDR", codice=m.group(1))

    m = re.search(rf"\b({_POD_CODE})\b", text)
    if m:
        return PuntoFornitura(tipo="POD", codice=m.group(1).upper())

    return PuntoFornitura()


def extract_numero_fattura(text: str) -> str | None:
    m = re.search(r"\b(KE-[A-Z0-9-]+)\b", text)
    if m:
        return m.group(1)
    m = re.search(r"Fattura\s+n[°º]?\s*(\d+)", text, re.I)
    if m:
        return m.group(1)
    return None


def extract_codice_fornitura(text: str) -> str | None:
    m = re.search(r"Codice\s+Fornitura:\s*([A-Z0-9-]+)", text, re.I)
    if m:
        return m.group(1)
    return None


def extract_fornitore(text: str) -> str | None:
    for name in _FORNITORI:
        if name in text:
            return name
    return None


def extract_subtotali(text: str) -> Subtotali | None:
    found: dict[str, float] = {}
    for field, label in _SUBTOTAL_PATTERNS:
        m = re.search(label, text, re.I)
        if not m:
            continue
        amount = _money_after(text, m.end(), window=400)
        if amount is not None:
            found[field] = amount

    altre_sum = 0.0
    altre_found = False
    for label in _ALTRE_PARTITE_LABELS:
        for m in re.finditer(label, text, re.I):
            amount = _money_after(text, m.end(), window=400)
            if amount is not None:
                altre_sum += amount
                altre_found = True
    if altre_found:
        found["altre_partite"] = round(altre_sum, 2)

    if len(found) < 2:
        return None
    return Subtotali(**found)


def parse_bill_text(text: str) -> BillMvp:
    bill = BillMvp(
        servizio=detect_servizio(text),
        fornitore=extract_fornitore(text),
        totale=extract_totale(text),
        scadenza=extract_scadenza(text),
        periodo=extract_periodo(text),
        consumo=extract_consumo(text),
        numero_fattura=extract_numero_fattura(text),
        codice_fornitura=extract_codice_fornitura(text),
        punto_fornitura=extract_punto(text),
        subtotali=extract_subtotali(text),
    )
    return finalize(bill)
