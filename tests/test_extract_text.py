from pathlib import Path

from parsers.extract_text import read_text_file


FIXTURES = Path(__file__).parent / "fixtures"


def test_read_text_file_octopus():
    text = read_text_file(FIXTURES / "octopus_luce.txt")
    assert "TOTALE DA PAGARE" in text
    assert "24,63" in text
