"""Numeric and clause-alignment comparison."""

from __future__ import annotations

import unittest

from plainpath.compare import compare_documents
from plainpath.samples import load_sample_pair


class TestCompare(unittest.TestCase):
    def test_renewal_only_has_auto_renew_and_rent_changes(self) -> None:
        text_a, text_b = load_sample_pair()
        report = compare_documents(text_a, text_b)
        titles_only_b = set(report.only_in_b)
        self.assertTrue(any("Automatic renewal" == title for title in titles_only_b))
        displays_a = {row.display_a for row in report.money_mismatches}
        displays_b = {row.display_b for row in report.money_mismatches}
        self.assertTrue(any("1450.00" in value for value in displays_a))
        self.assertTrue(any("1595.00" in value for value in displays_b))
        self.assertTrue(report.money_mismatches)
        self.assertTrue(any(row.delta_cents != 0 for row in report.money_mismatches))
        self.assertIn("lease", (report.type_a, report.type_b))

    def test_identical_texts_have_no_only_in_b(self) -> None:
        text_a, _ = load_sample_pair()
        report = compare_documents(text_a, text_a)
        self.assertEqual(report.only_in_b, ())
        self.assertEqual(report.money_mismatches, ())
        self.assertTrue(all(row.status == "same" for row in report.aligned))


if __name__ == "__main__":
    unittest.main()
