from parsers.money import parse_italian_date, parse_first_euro_importo, parse_last_euro_importo, parse_money


def test_parse_money_italian_comma():
    assert parse_money("24,63 €") == 24.63
    assert parse_money("45,58€") == 45.58
    assert parse_money("-4,76 €") == -4.76


def test_parse_money_invalid():
    assert parse_money("") is None
    assert parse_money("n/a") is None


def test_parse_last_euro_importo_skips_qty_and_unit_price():
    line = "45 kWh x                         0,19 €/kWh                                              8,54 €"
    assert parse_last_euro_importo(line) == 8.54
    assert parse_last_euro_importo("7,92 €/mese                                              7,92 €") == 7.92
    assert parse_last_euro_importo("only 0,19 €/kWh") is None


def test_parse_first_euro_importo_before_di_cui():
    line = (
        "Ricalcoli                                                                           -4,76 €"
        "       di cui spesa per la quota consumi:                         12,68 €"
    )
    assert parse_first_euro_importo(line) == -4.76
    assert parse_last_euro_importo(line) == 12.68


def test_parse_italian_date():
    assert parse_italian_date("28/08/2026") == "2026-08-28"
    assert parse_italian_date("07/04/2026") == "2026-04-07"
    assert parse_italian_date("bad") is None
