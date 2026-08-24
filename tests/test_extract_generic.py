from pathlib import Path

from parsers.extract_generic import (
    extract_fornitore,
    extract_punto,
    extract_subtotali,
    parse_bill_text,
)
from parsers.extract_text import read_text_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_octopus_luce_mvp():
    text = read_text_file(FIXTURES / "octopus_luce.txt")
    bill = parse_bill_text(text)
    assert bill.servizio == "elettrico"
    assert bill.totale == 24.63
    assert bill.scadenza == "2026-08-28"
    assert bill.periodo["dal"] == "2026-07-01"
    assert bill.periodo["al"] == "2026-07-31"
    assert bill.consumo.valore == 45.0
    assert bill.consumo.unita == "kWh"
    assert bill.punto_fornitura.tipo == "POD"
    assert bill.punto_fornitura.codice == "IT221E00704700"
    assert bill.numero_fattura == "KE-26-F4AD1939-004"
    assert bill.fornitore == "Octopus Energy"
    assert bill.subtotali is not None
    assert bill.check.subtotali_ok is True
    assert bill.status == "ok"


def test_nen_gas_sintesi_mvp():
    text = read_text_file(FIXTURES / "nen_gas_sintesi.txt")
    bill = parse_bill_text(text)
    assert bill.servizio == "gas"
    assert bill.totale == 45.58
    assert bill.scadenza == "2026-04-07"
    assert bill.periodo["dal"] == "2026-03-01"
    assert bill.periodo["al"] == "2026-03-31"
    assert bill.consumo.valore == 31.0
    assert bill.consumo.unita == "Smc"
    assert bill.punto_fornitura.tipo == "PDR"
    assert bill.punto_fornitura.codice == "07990001032047"
    assert bill.numero_fattura == "261261166"
    assert bill.fornitore == "NeN"
    assert bill.subtotali is not None
    assert bill.check.subtotali_ok is True
    assert bill.status == "ok"


def test_extract_subtotali_prefers_importo_over_quantity():
    """Real Octopus layout: qty/unit price before the line importo."""
    text = """
Quota per consumi

                                                                     45 kWh x                         0,19 €/kWh                                              8,54 €

Quota fissa

                                                                       1 mese x                      7,92 €/mese                                              7,92 €

Quota potenza

                                                                         3 kW x                        1,98 €/kW                                              5,93 €

Accise e IVA                                                                                2,24 €
"""
    sub = extract_subtotali(text)
    assert sub is not None
    assert sub.quota_consumi == 8.54
    assert sub.quota_fissa == 7.92
    assert sub.quota_potenza == 5.93
    assert sub.accise_iva == 2.24


def test_extract_subtotali_multiline_qty_before_importo():
    """pdftotext -layout: quantity on its own line before the euro importo."""
    text = """
Quota per consumi

45 kWh

8,54 €

Quota fissa

7,92 €
"""
    sub = extract_subtotali(text)
    assert sub is not None
    assert sub.quota_consumi == 8.54
    assert sub.quota_fissa == 7.92


def test_extract_consumo_ignores_stray_kwh_without_label():
    from parsers.extract_generic import extract_consumo

    text = "random 100 kWh unrelated\nCONSUMO FATTURATO: 45 kWh"
    consumo = extract_consumo(text)
    assert consumo.valore == 45.0
    assert consumo.unita == "kWh"

    text_no_label = "random 100 kWh before real\nlater 45 kWh in footer"
    consumo2 = extract_consumo(text_no_label)
    assert consumo2.valore is None
    assert consumo2.unita is None


def test_extract_subtotali_includes_bonus_applicati_in_altre_partite():
    """Octopus: Bonus applicati reduce TOTALE DA PAGARE vs TOTALE BOLLETTA."""
    text = """
Quota per consumi
73 kWh x 0,17 €/kWh 12,12 €
Quota fissa
1 mese x 7,92 €/mese 7,92 €
Quota potenza
3 kW x 1,98 €/kW 5,93 €
Accise e IVA 2,60 €
TOTALE BOLLETTA 28,57 €
Bonus applicati -1,21 €
TOTALE DA PAGARE 27,36 €
Entro il 26/06/2026
"""
    sub = extract_subtotali(text)
    assert sub is not None
    assert sub.altre_partite == -1.21
    bill = parse_bill_text(text)
    assert bill.totale == 27.36
    assert bill.check.subtotali_ok is True
    assert bill.status == "ok"


def test_extract_subtotali_sums_bonus_and_credito_rimanente():
    """Octopus zero-due bill: bonus overshoots, credito rimanente closes to 0."""
    text = """
Quota per consumi
75 kWh x 0,16 €/kWh 12,32 €
Quota fissa
1 mese x 7,92 €/mese 7,92 €
Quota potenza
3 kW x 1,98 €/kW 5,93 €
Accise e IVA 2,62 €
TOTALE BOLLETTA 28,79 €
Bonus applicati -30,00 €
TOTALE DA PAGARE 0,00 €
Credito rimanente 1,21 €
Entro il 03/06/2026
"""
    sub = extract_subtotali(text)
    assert sub is not None
    assert sub.altre_partite == -28.79  # -30.00 + 1.21
    bill = parse_bill_text(text)
    assert bill.totale == 0.0
    assert bill.check.subtotali_ok is True
    assert bill.status == "ok"


def test_extract_fornitore_returns_short_name():
    footer = (
        "Octopus Energy Italia Srl, società a socio unico soggetta "
        "all'attività di direzione e coordinamento di Octopus Energy Group Limited"
    )
    assert extract_fornitore(footer) == "Octopus Energy"
    assert extract_fornitore("NeN - YADA Energia S.r.l.") == "NeN"


def test_extract_punto_prefers_pdr_over_iban_fragment():
    """NeN sintesi: PDR on next line after side header; IBAN has IT85B fragment."""
    text = """
        PDR                                                                                               Codice offerta
        07990001032047                                                                                    029748GPFML01XX260301GDDUER00000

 • Bonifico bancario intestato a Yada Energia S.r.l. IBAN IT85B 01005 01600 000000014930
"""
    punto = extract_punto(text)
    assert punto.tipo == "PDR"
    assert punto.codice == "07990001032047"


def test_extract_punto_rejects_short_iban_as_pod():
    text = "IBAN IT85B 01005 01600 000000014930"
    punto = extract_punto(text)
    assert punto.codice is None
    assert punto.tipo is None


def test_extract_punto_accepts_full_pod_without_label():
    text = "POD del punto: IT221E00704700 in bolletta"
    punto = extract_punto(text)
    assert punto.tipo == "POD"
    assert punto.codice == "IT221E00704700"
