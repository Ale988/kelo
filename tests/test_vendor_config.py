from pathlib import Path

from parsers.extract_text import read_text_file
from parsers.vendor_config import (
    classify_vendor,
    default_vendors_dir,
    extract_email,
    load_vendor_profiles,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_classify_octopus_fixture_by_text():
    text = read_text_file(FIXTURES / "octopus_luce.txt")
    result = classify_vendor(text, filename="octopus_luce.txt")
    assert result.vendor_profile == "octopus_luce"
    assert result.match_source == "text"
    assert result.ambiguous is False


def test_classify_nen_fixture_by_text():
    text = read_text_file(FIXTURES / "nen_gas_sintesi.txt")
    result = classify_vendor(text, filename="bolletta_di_sintesi_aprile.txt")
    assert result.vendor_profile == "nen_gas_sintesi"
    assert result.match_source == "text"
    assert result.ambiguous is False


def test_classify_by_sender_octopus():
    text = read_text_file(FIXTURES / "octopus_luce.txt")
    result = classify_vendor(
        text,
        sender="Octopus Energy <ciao@octopusenergy.it>",
    )
    assert result.vendor_profile == "octopus_luce"
    assert result.match_source == "sender"


def test_classify_hint_overrides_sender():
    text = read_text_file(FIXTURES / "octopus_luce.txt")
    result = classify_vendor(
        text,
        sender="ciao@octopusenergy.it",
        hint="nen_gas_sintesi",
    )
    assert result.vendor_profile == "nen_gas_sintesi"
    assert result.match_source == "hint"
    assert result.warnings == ()


def test_classify_hint_unknown_profile_warns():
    result = classify_vendor("x", hint="nonexistent_profile_xyz")
    assert result.vendor_profile == "nonexistent_profile_xyz"
    assert result.match_source == "hint"
    assert result.warnings == ("vendor_profile_unknown",)


def test_classify_unknown_text_returns_none():
    result = classify_vendor("Random document without bill markers")
    assert result.vendor_profile is None
    assert result.match_source is None
    assert result.ambiguous is False


def test_classify_ambiguous_when_two_profiles_tie(tmp_path):
    vendors = tmp_path / "vendors"
    vendors.mkdir()
    (vendors / "a.yaml").write_text(
        """
vendor_category: vendor_a
classification:
  text_keywords: [SHARED]
  require_keywords: []
""",
        encoding="utf-8",
    )
    (vendors / "b.yaml").write_text(
        """
vendor_category: vendor_b
classification:
  text_keywords: [SHARED]
  require_keywords: []
""",
        encoding="utf-8",
    )
    result = classify_vendor("SHARED marker only", vendors_dir=vendors)
    assert result.vendor_profile is None
    assert result.ambiguous is True
    assert result.match_source == "text"


def test_extract_email_from_header():
    assert extract_email("Octopus <ciao@octopusenergy.it>") == "ciao@octopusenergy.it"


def test_bundled_vendor_profiles_ship_with_package():
    root = default_vendors_dir()
    assert root.is_dir()
    assert root.parent.name == "parsers"
    profiles = load_vendor_profiles()
    categories = {p.vendor_category for p in profiles}
    assert categories == {"octopus_luce", "nen_gas_sintesi"}
