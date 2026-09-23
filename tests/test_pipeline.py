"""End-to-end local pipeline without a network."""

from __future__ import annotations

import unittest
from datetime import date

from plainpath.llm import MockLLM, build_llm
from plainpath.config import Settings
from plainpath.pipeline import analyze_document, narrate_simplify
from plainpath.samples import load_sample


class TestPipeline(unittest.TestCase):
    def test_analyze_employment_sheet_has_salary_and_noncompete(self) -> None:
        text = load_sample("Harborline employment agreement")
        analysis = analyze_document(text, today=date(2026, 1, 20), persona_id="worker")
        self.assertEqual(analysis.facts.document_type, "employment")
        self.assertTrue(any("72000" in item.display for item in analysis.facts.money))
        kinds = {hit.kind for hit in analysis.facts.clauses}
        self.assertIn("non_compete", kinds)
        self.assertIn("arbitration", kinds)

    def test_mock_narration_does_not_raise(self) -> None:
        text = load_sample("CloudNest consumer terms")
        analysis = analyze_document(text, today=date(2026, 9, 22), persona_id="consumer")
        result = narrate_simplify(
            MockLLM(), analysis, persona_id="consumer", literacy="plain", language="English"
        )
        self.assertTrue(result.degraded)
        self.assertIn("Mock", result.text)

    def test_build_llm_mock_when_provider_forced(self) -> None:
        settings = Settings(
            llm_provider="mock",
            gemini_api_key=None,
            google_api_key=None,
            groq_api_key=None,
            openai_api_key=None,
        )
        client = build_llm(settings)
        self.assertEqual(client.name(), "mock")
        self.assertFalse(client.is_live())


if __name__ == "__main__":
    unittest.main()
