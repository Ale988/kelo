from parsers.schema import BillMvp, Consumo, PuntoFornitura, Subtotali, Check, finalize


def test_finalize_ok_when_total_due_and_subtotals_match():
    bill = BillMvp(
        servizio="elettrico",
        fornitore="Octopus Energy",
        totale=24.63,
        scadenza="2026-08-28",
        periodo={"dal": "2026-07-01", "al": "2026-07-31"},
        consumo=Consumo(valore=45.0, unita="kWh"),
        numero_fattura="KE-26-F4AD1939-004",
        codice_fornitura="A-F4AD1939",
        punto_fornitura=PuntoFornitura(tipo="POD", codice="IT221E00704700"),
        subtotali=Subtotali(
            quota_consumi=8.54,
            quota_fissa=7.92,
            quota_potenza=5.93,
            ricalcoli=None,
            altre_partite=None,
            accise_iva=2.24,
        ),
        check=Check(),
        status="ok",
        warnings=[],
    )
    out = finalize(bill)
    assert out.check.subtotali_ok is True
    assert abs(out.check.delta or 0) <= 0.02
    assert out.status == "ok"


def test_finalize_parse_failed_without_totale():
    bill = BillMvp(totale=None, scadenza="2026-08-28")
    out = finalize(bill)
    assert out.status == "parse_failed"


def test_finalize_parse_failed_without_scadenza():
    bill = BillMvp(totale=24.63, scadenza=None)
    out = finalize(bill)
    assert out.status == "parse_failed"


def test_finalize_da_controllare_when_subtotals_mismatch():
    bill = BillMvp(
        servizio="gas",
        totale=45.58,
        scadenza="2026-04-07",
        subtotali=Subtotali(quota_consumi=10.0, quota_fissa=10.0),
    )
    out = finalize(bill)
    assert out.check.subtotali_ok is False
    assert out.status == "da_controllare"


def test_finalize_skips_subtotal_check_when_missing():
    bill = BillMvp(servizio="gas", totale=45.58, scadenza="2026-04-07", subtotali=None)
    out = finalize(bill)
    assert out.check.subtotali_ok is None
    assert out.status == "ok"
