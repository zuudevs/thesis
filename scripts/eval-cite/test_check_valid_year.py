from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from check_valid_year import ALLOWED_PRE_2016, BIB_PATH, check_valid_year, parse_bib_entries


class ValidYearTests(unittest.TestCase):
    def test_canonical_bibliography_passes_with_explicit_exception(self) -> None:
        self.assertEqual(check_valid_year(BIB_PATH), [])
        entries = parse_bib_entries(BIB_PATH)
        for key in ALLOWED_PRE_2016:
            self.assertIn(key, entries)

    def test_unlisted_pre_2016_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.bib"
            path.write_text("@article{old,\nyear = {2015}\n}\n", encoding="utf-8")
            violations = check_valid_year(path)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["key"], "old")
        self.assertEqual(violations[0]["year"], 2015)

    def test_missing_year_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.bib"
            path.write_text("@article{unknown,\ntitle = {No year}\n}\n", encoding="utf-8")
            violations = check_valid_year(path)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "missing year")

    def test_duplicate_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.bib"
            path.write_text(
                "@article{same,\nyear = {2020}\n}\n@article{same,\nyear = {2021}\n}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate BibTeX key: same"):
                parse_bib_entries(path)


if __name__ == "__main__":
    unittest.main()
