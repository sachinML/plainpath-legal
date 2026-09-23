"""Next-step routing and briefing pack contents."""

from __future__ import annotations

import unittest
from datetime import date

from plainpath.brief import brief_to_markdown
from plainpath.pipeline import analyze_document
from plainpath.samples import load_sample
from plainpath.types import DISCLAIMER


class TestNextStepsAndBrief(unittest.TestCase):
    def test_high_risk_renewal_routes_lawyer_and_cancel_window(self) -> None:
        text = load_sample("Oakridge renewal (sample B — compare against A)")
        analysis = analyze_document(
            text, today=date(2027, 1, 20), persona_id="tenant", source_name="renewal"
        )
        codes = {step.code for step in analysis.next_steps}
        self.assertIn("not_advice", codes)
        self.assertIn("cancel_window", codes)
        self.assertTrue({"lawyer_before_sign", "lawyer_questions"} & codes)
        self.assertGreaterEqual(analysis.facts.risk.score, 25)

    def test_community_navigator_gets_access_step(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        analysis = analyze_document(
            text, today=date(2026, 9, 22), persona_id="community_navigator"
        )
        codes = {step.code for step in analysis.next_steps}
        self.assertIn("access_supports", codes)

    def test_worker_noncompete_step_on_employment_sample(self) -> None:
        text = load_sample("Harborline employment agreement")
        analysis = analyze_document(text, today=date(2026, 1, 20), persona_id="worker")
        codes = {step.code for step in analysis.next_steps}
        self.assertIn("noncompete", codes)

    def test_brief_markdown_contains_disclaimer_and_access_list(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        analysis = analyze_document(text, today=date(2026, 9, 22), persona_id="tenant")
        markdown = brief_to_markdown(
            analysis.brief,
            persona_label="Tenant / renter",
            source_name="lease",
            disclaimer=DISCLAIMER,
        )
        self.assertIn("not a lawyer", markdown.lower())
        self.assertIn("interpreter", markdown.lower())
        self.assertIn("Watchfulness score", markdown)


if __name__ == "__main__":
    unittest.main()
