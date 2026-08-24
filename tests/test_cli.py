import json
from pathlib import Path

from parsers.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_json_stdout_for_txt(capsys):
    code = main([str(FIXTURES / "octopus_luce.txt")])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["totale"] == 24.63
    assert data["status"] == "ok"
    assert data["vendor_profile"] == "octopus_luce"
    assert data["vendor_match_source"] == "text"


def test_cli_vendor_hint(capsys):
    code = main(
        [
            str(FIXTURES / "octopus_luce.txt"),
            "--vendor",
            "custom_profile",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["vendor_profile"] == "custom_profile"
    assert data["vendor_match_source"] == "hint"
    assert "vendor_profile_unknown" in data["warnings"]


def test_cli_missing_file(capsys):
    code = main(["/nonexistent/bill.txt"])
    assert code == 2
    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_cli_sender_classification(capsys):
    code = main(
        [
            str(FIXTURES / "octopus_luce.txt"),
            "--sender",
            "ciao@octopusenergy.it",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["vendor_profile"] == "octopus_luce"
    assert data["vendor_match_source"] == "sender"
