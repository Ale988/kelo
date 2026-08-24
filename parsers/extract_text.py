from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def read_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def extract_text_from_pdf(path: str | Path) -> str:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        proc = subprocess.run(
            [pdftotext, "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout

    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(
            "pdftotext failed/missing and pypdf is not installed; "
            "install poppler or pip install 'kelo-parsers[pdf]'"
        ) from e

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts)
    if not text.strip():
        raise RuntimeError(f"No text extracted from {path}")
    return text
