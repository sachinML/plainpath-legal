"""Flesch math stays in code."""

from __future__ import annotations

import unittest

from plainpath.readability import count_syllables, ease_label, flesch_scores


class TestReadability(unittest.TestCase):
    def test_short_easy_sentence_is_easier_than_legal_sentence(self) -> None:
        easy, easy_grade = flesch_scores("The cat sat on the mat. The dog ran.")
        hard, hard_grade = flesch_scores(
            "Notwithstanding the foregoing indemnification, the undersigned hereby "
            "irrevocably waives any and all claims arising hereunder."
        )
        self.assertGreater(easy, hard)
        self.assertLess(easy_grade, hard_grade)

    def test_syllable_helper_and_labels(self) -> None:
        self.assertGreaterEqual(count_syllables("automatically"), 4)
        self.assertIn("dense", ease_label(10))
        self.assertIn("plain", ease_label(90))


if __name__ == "__main__":
    unittest.main()
