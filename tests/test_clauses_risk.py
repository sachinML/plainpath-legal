"""Clause flags, gap watch, and deterministic risk math."""

from __future__ import annotations

import unittest

from plainpath.clauses import detect_clauses
from plainpath.gaps import find_gaps
from plainpath.risk import score_risk
from plainpath.samples import load_sample


class TestClauses(unittest.TestCase):
    def test_renewal_flags_auto_renew_and_arbitration(self) -> None:
        text = load_sample("Oakridge renewal (sample B — compare against A)")
        kinds = {hit.kind for hit in detect_clauses(text)}
        self.assertIn("auto_renewal", kinds)
        self.assertIn("arbitration", kinds)
        self.assertIn("class_waiver", kinds)

    def test_original_lease_does_not_flag_auto_renew(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        kinds = {hit.kind for hit in detect_clauses(text)}
        self.assertNotIn("auto_renewal", kinds)
        self.assertIn("late_fee", kinds)
        self.assertIn("entry", kinds)


class TestGaps(unittest.TestCase):
    def test_renewal_missing_repair_and_entry_notice_for_tenant(self) -> None:
        text = load_sample("Oakridge renewal (sample B — compare against A)")
        gaps = find_gaps(text, "lease", "tenant")
        topics = {gap.topic for gap in gaps}
        self.assertIn("Repair or habitability timeline", topics)
        self.assertIn("Advance notice before entry", topics)

    def test_original_lease_mentions_repairs_so_that_gap_is_absent(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        gaps = find_gaps(text, "lease", "tenant")
        topics = {gap.topic for gap in gaps}
        self.assertNotIn("Repair or habitability timeline", topics)

    def test_community_navigator_sees_access_gap_when_unmentioned(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        gaps = find_gaps(text, "lease", "community_navigator")
        topics = {gap.topic for gap in gaps}
        self.assertIn("Interpreter or accessible format", topics)


class TestRisk(unittest.TestCase):
    def test_score_is_bounded_and_higher_when_high_flags_stack(self) -> None:
        quiet = detect_clauses("This is a short note with no special terms.")
        noisy = detect_clauses(
            "This shall automatically renew. Binding arbitration. Class action waiver. "
            "Employee shall indemnify and hold harmless the company. Non-compete follows."
        )
        quiet_report = score_risk(quiet)
        noisy_report = score_risk(noisy)
        self.assertEqual(quiet_report.score, 0)
        self.assertEqual(quiet_report.band, "low")
        self.assertGreaterEqual(noisy_report.score, 50)
        self.assertEqual(noisy_report.band, "high")
        self.assertLessEqual(noisy_report.score, 100)
        self.assertTrue(any("Arbitration plus a class waiver" in line for line in noisy_report.drivers))

    def test_noncompete_duration_adds_weight(self) -> None:
        from plainpath.extract import extract_durations

        text = "Employee agrees to a non-compete for eighteen (18) months after employment ends."
        clauses = detect_clauses(text)
        durations = extract_durations(text)
        with_extra = score_risk(clauses, durations=durations)
        without = score_risk(clauses)
        self.assertGreater(with_extra.score, without.score)


if __name__ == "__main__":
    unittest.main()
