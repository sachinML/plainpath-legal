"""Tests for money, dates, parties, durations, and document typing."""

from __future__ import annotations

import unittest
from datetime import date

from plainpath.extract import (
    classify_document,
    extract_dates,
    extract_durations,
    extract_governing_law,
    extract_money,
    extract_parties,
    parse_money_to_cents,
    parse_today,
)
from plainpath.samples import load_sample


class TestMoney(unittest.TestCase):
    def test_parse_cents_with_comma_and_decimals(self) -> None:
        self.assertEqual(parse_money_to_cents("1,450.00"), 145000)
        self.assertEqual(parse_money_to_cents("12.99"), 1299)
        self.assertEqual(parse_money_to_cents("45"), 4500)

    def test_lease_extracts_rent_and_deposit(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        money = extract_money(text)
        displays = {item.display for item in money}
        self.assertIn("USD 1450.00", displays)
        self.assertTrue(any("late" in item.label or "late" in item.source.lower() for item in money))


class TestDatesAndDurations(unittest.TestCase):
    def test_days_from_as_of_are_subtracted_in_code(self) -> None:
        text = "The term begins on March 1, 2026 and ends on February 28, 2027."
        today = date(2026, 3, 1)
        items = extract_dates(text, today)
        values = {item.value: item.days_from_today for item in items}
        self.assertIn(date(2026, 3, 1), values)
        self.assertEqual(values[date(2026, 3, 1)], 0)
        self.assertEqual(values[date(2027, 2, 28)], (date(2027, 2, 28) - today).days)

    def test_duration_eighteen_months_in_parentheses(self) -> None:
        text = "For eighteen (18) months after employment ends, Employee shall not compete."
        durations = extract_durations(text)
        self.assertTrue(any(item.quantity == 18 and item.days_approx == 18 * 30 for item in durations))

    def test_parse_today_rejects_garbage(self) -> None:
        fallback = date(2026, 9, 22)
        self.assertEqual(parse_today("not-a-date", fallback=fallback), fallback)
        self.assertEqual(parse_today("2026-01-15", fallback=fallback), date(2026, 1, 15))


class TestPartiesAndLaw(unittest.TestCase):
    def test_named_parties_and_iowa_law(self) -> None:
        text = load_sample("Oakridge lease (sample A)")
        parties = extract_parties(text)
        roles = {party.role: party.name for party in parties}
        self.assertEqual(roles.get("landlord"), "Oakridge Court LLC")
        self.assertEqual(roles.get("tenant"), "Jordan Hale")
        self.assertEqual(extract_governing_law(text), "Iowa")

    def test_classify_lease_and_employment(self) -> None:
        lease = load_sample("Oakridge lease (sample A)")
        job = load_sample("Harborline employment agreement")
        self.assertEqual(classify_document(lease)[0], "lease")
        self.assertEqual(classify_document(job)[0], "employment")


if __name__ == "__main__":
    unittest.main()
