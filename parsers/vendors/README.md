# Vendor profiles

YAML profiles for deterministic bill parsing. Shipped inside the `parsers` package so `pip install` (non-editable) still finds them.

**Status:** `classification` is wired via `parsers/vendor_config.py` and the CLI (`--vendor`, `--sender`). The `parsing` section is reference/spec for authors — extraction runs in `parsers/extract_generic.py` until a YAML-driven interpreter exists.

## Layout

```
parsers/vendors/
  octopus_luce.yaml
  nen_gas_sintesi.yaml
```

## Adding a vendor

1. Save an anonymised `.txt` extract under `tests/fixtures/`.
2. Copy an existing YAML and fill `classification`, `parsing`, `required_fields`.
3. Add a test that loads the fixture and asserts `BillMvp` fields.
4. Wire the profile in code only when the generic extractor misses systematically.
