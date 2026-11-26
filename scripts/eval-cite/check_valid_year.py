"""Validate the publication-year policy for the canonical bibliography.

Entries published before 2016 are rejected unless they are explicitly listed
in ``ALLOWED_PRE_2016`` with a scholarly reason.  The exception is key-based
so a missing year cannot accidentally inherit another entry's approval.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIB_PATH = ROOT / "assets" / "bib" / "cites.bib"
MIN_YEAR = 2016

ALLOWED_PRE_2016 = {
    "10.1145_2807591.2807644": (
        "Foundational SC'15 benchmark-reporting methodology; retained as the "
        "article's explicit pre-2016 methodology exception."
    ),
}

_ENTRY_RE = re.compile(r"(?mi)^@(\w+)\{([^,]+),")
_YEAR_RE = re.compile(r"(?mi)^\s*year\s*=\s*[\{\"']?(\d{4})[\}\"']?")


def parse_bib_entries(path: Path) -> dict[str, int | None]:
    """Return ``{citation_key: year}`` for all entries in a BibTeX file."""
    text = path.read_text(encoding="utf-8-sig")
    matches = list(_ENTRY_RE.finditer(text))
    entries: dict[str, int | None] = {}

    for index, match in enumerate(matches):
        key = match.group(2).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start():end]
        year_match = _YEAR_RE.search(body)
        year = int(year_match.group(1)) if year_match else None
        if key in entries:
            raise ValueError(f"duplicate BibTeX key: {key}")
        entries[key] = year
    return entries


def check_valid_year(path: Path = BIB_PATH) -> list[dict[str, object]]:
    """Return entries that violate the year policy."""
    violations: list[dict[str, object]] = []
    for key, year in parse_bib_entries(path).items():
        if key in ALLOWED_PRE_2016:
            continue
        if year is None:
            violations.append({"key": key, "year": None, "reason": "missing year"})
        elif year < MIN_YEAR:
            violations.append({"key": key, "year": year, "reason": f"year < {MIN_YEAR}"})
    return violations


def main() -> int:
    entries = parse_bib_entries(BIB_PATH)
    violations = check_valid_year(BIB_PATH)

    for key, (reason) in ALLOWED_PRE_2016.items():
        year = entries.get(key)
        if year is None:
            print(f"ALLOWLIST STALE: {key} is no longer present")
        elif year < MIN_YEAR:
            print(f"ALLOWED: {key} ({year}) — {reason}")

    if violations:
        print(f"FAIL: {len(violations)} bibliography entr{'y' if len(violations) == 1 else 'ies'} violate the year policy")
        for violation in violations:
            print(f" - {violation['key']}: {violation['reason']}")
        return 1

    print(f"PASS: {len(entries)} entries satisfy year >= {MIN_YEAR} or the explicit exception policy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
