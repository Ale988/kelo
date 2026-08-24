from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SUBTOTAL_TOLERANCE = 0.02

Servizio = Literal["elettrico", "gas"] | None
UnitaConsumo = Literal["kWh", "Smc"] | None
TipoPunto = Literal["POD", "PDR"] | None
Status = Literal["ok", "da_controllare", "parse_failed"]


@dataclass
class Consumo:
    valore: float | None = None
    unita: UnitaConsumo = None


@dataclass
class PuntoFornitura:
    tipo: TipoPunto = None
    codice: str | None = None


@dataclass
class Subtotali:
    quota_consumi: float | None = None
    quota_fissa: float | None = None
    quota_potenza: float | None = None
    ricalcoli: float | None = None
    altre_partite: float | None = None
    accise_iva: float | None = None

    def sum_present(self) -> float | None:
        vals = [
            self.quota_consumi,
            self.quota_fissa,
            self.quota_potenza,
            self.ricalcoli,
            self.altre_partite,
            self.accise_iva,
        ]
        present = [v for v in vals if v is not None]
        if not present:
            return None
        return round(sum(present), 2)


@dataclass
class Check:
    subtotali_ok: bool | None = None
    delta: float | None = None


@dataclass
class BillMvp:
    servizio: Servizio = None
    fornitore: str | None = None
    totale: float | None = None
    scadenza: str | None = None
    periodo: dict[str, str | None] = field(
        default_factory=lambda: {"dal": None, "al": None}
    )
    consumo: Consumo = field(default_factory=Consumo)
    numero_fattura: str | None = None
    codice_fornitura: str | None = None
    punto_fornitura: PuntoFornitura = field(default_factory=PuntoFornitura)
    subtotali: Subtotali | None = None
    check: Check = field(default_factory=Check)
    status: Status = "parse_failed"
    warnings: list[str] = field(default_factory=list)
    vendor_profile: str | None = None
    vendor_match_source: Literal["hint", "sender", "text"] | None = None


def finalize(bill: BillMvp) -> BillMvp:
    """Set status, check, and warnings on ``bill`` (mutates in place)."""
    if bill.totale is None or bill.scadenza is None:
        bill.status = "parse_failed"
        bill.check = Check(subtotali_ok=None, delta=None)
        return bill

    if bill.subtotali is None:
        bill.check = Check(subtotali_ok=None, delta=None)
    else:
        s = bill.subtotali.sum_present()
        if s is None:
            bill.check = Check(subtotali_ok=None, delta=None)
        else:
            delta = round(s - bill.totale, 2)
            ok = abs(delta) <= SUBTOTAL_TOLERANCE
            bill.check = Check(subtotali_ok=ok, delta=delta)

    if bill.check.subtotali_ok is False:
        bill.status = "da_controllare"
    elif bill.servizio is None and (
        bill.punto_fornitura.codice is None or bill.consumo.valore is None
    ):
        bill.status = "da_controllare"
        bill.warnings.append("servizio_unclear")
    else:
        bill.status = "ok"
    return bill


def bill_to_dict(bill: BillMvp) -> dict[str, Any]:
    return asdict(bill)
