"""Local retrieval must return the paragraph that actually contains the query terms."""

from __future__ import annotations

import unittest

from plainpath.retrieve import retrieve, tokenize
from plainpath.samples import load_sample


class TestRetrieve(unittest.TestCase):
    def test_auto_renewal_query_ranks_the_renewal_sentence(self) -> None:
        text = load_sample("Oakridge renewal (sample B — compare against A)")
        chunks = retrieve(text, "Does this lease automatically renew?", k=3)
        self.assertTrue(chunks)
        joined = " ".join(chunk.text.lower() for chunk in chunks)
        self.assertIn("automatically renew", joined)
        self.assertGreater(chunks[0].score, 0)

    def test_deposit_query_on_original_lease(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        chunks = retrieve(text, "How is the security deposit returned?", k=2)
        joined = " ".join(chunk.text.lower() for chunk in chunks)
        self.assertIn("security deposit", joined)

    def test_empty_document_returns_no_chunks(self) -> None:
        self.assertEqual(retrieve("   ", "anything"), ())

    def test_tokenizer_drops_stopwords(self) -> None:
        tokens = tokenize("The tenant must pay the rent")
        self.assertIn("tenant", tokens)
        self.assertIn("rent", tokens)
        self.assertNotIn("the", tokens)


if __name__ == "__main__":
    unittest.main()
