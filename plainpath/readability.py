"""Deterministic readability scores (Flesch). The LLM never computes these."""

from __future__ import annotations

import re

_VOWELS = set("aeiouy")


def count_words(text: str) -> int:
    """Count word-like tokens."""
    return len(re.findall(r"[A-Za-z0-9']+", text))


def count_sentences(text: str) -> int:
    """Count sentence-ending punctuation, with a floor of 1 for non-empty text."""
    bits = re.findall(r"[.!?]+", text)
    if bits:
        return len(bits)
    return 1 if text.strip() else 0


def count_syllables(word: str) -> int:
    """Heuristic English syllable count used only for reading-ease math."""
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned:
        return 0
    if len(cleaned) <= 3:
        return 1
    syllables = 0
    prev_vowel = False
    for char in cleaned:
        is_vowel = char in _VOWELS
        if is_vowel and not prev_vowel:
            syllables += 1
        prev_vowel = is_vowel
    if cleaned.endswith("e") and syllables > 1:
        syllables -= 1
    return max(1, syllables)


def flesch_scores(text: str) -> tuple[float, float]:
    """
    Return (reading_ease, grade_level) for `text`.

    Ease: higher is easier (about 90–100 = very easy, 0–30 = college/legal).
    Grade: U.S. grade-level estimate.
    """
    words = max(1, count_words(text))
    sentences = max(1, count_sentences(text))
    syllables = 0
    for token in re.findall(r"[A-Za-z0-9']+", text):
        syllables += count_syllables(token)
    syllables = max(1, syllables)
    ease = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    return round(ease, 1), round(max(0.0, grade), 1)


def ease_label(ease: float) -> str:
    """Map a Flesch ease score to a short text label (not color-only)."""
    if ease >= 70:
        return "plain language (around middle-school)"
    if ease >= 50:
        return "fairly plain (around high-school)"
    if ease >= 30:
        return "dense (around college)"
    return "very dense (specialist / legal)"
