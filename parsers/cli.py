from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from parsers.extract_generic import parse_bill_text
from parsers.extract_text import extract_text_from_pdf, read_text_file
from parsers.schema import bill_to_dict
from parsers.vendor_config import classify_vendor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse an Italian utility bill PDF/TXT to MVP JSON")
    parser.add_argument("path", type=Path, help="Path to .pdf or .txt")
    parser.add_argument(
        "--vendor",
        metavar="PROFILE",
        help="Force vendor profile slug (e.g. octopus_luce). Skips auto-classification.",
    )
    parser.add_argument(
        "--sender",
        metavar="FROM",
        help="Email From header for vendor classification (e.g. ciao@octopusenergy.it).",
    )
    args = parser.parse_args(argv)

    path: Path = args.path
    suffix = path.suffix.lower()
    if suffix not in {".txt", ".pdf"}:
        print(f"Unsupported file type: {path.suffix}", file=sys.stderr)
        return 2

    try:
        if suffix == ".txt":
            text = read_text_file(path)
        else:
            text = extract_text_from_pdf(path)
    except FileNotFoundError:
        print(f"File not found: {path}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    classification = classify_vendor(
        text,
        filename=path.name,
        sender=args.sender,
        hint=args.vendor,
    )
    bill = parse_bill_text(text)
    bill.vendor_profile = classification.vendor_profile
    bill.vendor_match_source = classification.match_source
    if classification.ambiguous:
        bill.warnings.append("vendor_ambiguous")
    bill.warnings.extend(classification.warnings)
    json.dump(bill_to_dict(bill), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if bill.status != "parse_failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
