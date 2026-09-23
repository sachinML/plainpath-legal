"""Prompts must include extracted facts and the no-invention rule."""

from __future__ import annotations

import unittest
from datetime import date

from plainpath.pipeline import analyze_document
from plainpath.prompts import qa_prompt, simplify_prompt
from plainpath.retrieve import retrieve
from plainpath.samples import load_sample
from plainpath.types import PERSONAS


class TestPrompts(unittest.TestCase):
    def test_simplify_prompt_contains_facts_and_forbids_invention(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        analysis = analyze_document(text, today=date(2026, 9, 22), persona_id="tenant")
        system, user = simplify_prompt(analysis.facts, PERSONAS[0], "plain", "English")
        self.assertIn("Never invent", system)
        self.assertIn("not a lawyer", system.lower())
        self.assertIn("1450", user)
        self.assertIn("FACTS_JSON", user)
        self.assertIn("watchfulness_score", user)

    def test_qa_prompt_only_gets_retrieved_excerpts(self) -> None:
        text = load_sample("CloudNest consumer terms")
        chunks = retrieve(text, "How do I cancel?", k=2)
        system, user = qa_prompt("How do I cancel?", chunks, PERSONAS[2], "plain", "English")
        self.assertIn("ONLY the excerpts", user)
        self.assertIn("QA_JSON", user)
        self.assertTrue(chunks)


if __name__ == "__main__":
    unittest.main()
