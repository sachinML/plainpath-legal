"""Model output and uploads must not carry active HTML or oversized files."""

from __future__ import annotations

import unittest

from plainpath.documents import MAX_DOC_CHARS, bytes_to_text, clip_text
from plainpath.sanitize import safe_markdown


class TestSanitize(unittest.TestCase):
    def test_strips_script_and_javascript_url(self) -> None:
        raw = 'Hello <script>alert(1)</script> [x](javascript:alert(1))'
        cleaned = safe_markdown(raw)
        self.assertNotIn("<script", cleaned.lower())
        self.assertNotIn("javascript:", cleaned.lower())
        self.assertIn("Hello", cleaned)

    def test_keeps_markdown_emphasis(self) -> None:
        raw = "Pay **USD 1450.00** on the first."
        self.assertIn("**USD 1450.00**", safe_markdown(raw))

    def test_strips_inline_event_handler(self) -> None:
        cleaned = safe_markdown('<img src="x" onerror="alert(1)">')
        self.assertNotIn("onerror=", cleaned.lower())


class TestDocumentLimits(unittest.TestCase):
    def test_clip_text_reports_when_trimmed(self) -> None:
        text, clipped = clip_text("abc", max_chars=2)
        self.assertEqual(text, "ab")
        self.assertTrue(clipped)
        again, clipped_again = clip_text("ab", max_chars=2)
        self.assertEqual(again, "ab")
        self.assertFalse(clipped_again)

    def test_rejects_oversize_payload(self) -> None:
        with self.assertRaises(ValueError):
            bytes_to_text("note.txt", b"x" * 50, max_bytes=10)

    def test_rejects_disallowed_suffix(self) -> None:
        with self.assertRaises(ValueError):
            bytes_to_text("payload.exe", b"not-a-doc")

    def test_decodes_plain_text(self) -> None:
        self.assertEqual(bytes_to_text("lease.txt", b"Rent is $10."), "Rent is $10.")

    def test_default_clip_bound_is_positive(self) -> None:
        self.assertGreater(MAX_DOC_CHARS, 1000)


if __name__ == "__main__":
    unittest.main()
