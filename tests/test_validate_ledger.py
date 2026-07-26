import unittest

from beancount import loader

from tools.validate_ledger import (
    ambiguous_account_segments,
    unused_open_accounts,
    used_accounts,
)


class AccountHygieneTests(unittest.TestCase):
    def test_reports_only_disallowed_complete_segments(self):
        accounts = {
            "Expenses:Services:General",
            "Expenses:Services:FixMe",
            "Expenses:Technology:Services:Other",
            "Expenses:Food:Otherworldly",
            "Assets:Bank:ICBC:Checking:4931",
        }

        self.assertEqual(
            ambiguous_account_segments(accounts),
            {
                "Expenses:Services:General": ("General",),
                "Expenses:Services:FixMe": ("FixMe",),
                "Expenses:Technology:Services:Other": ("Other",),
            },
        )

    def test_reports_open_accounts_without_any_ledger_reference(self):
        opens = {"Assets:Cash", "Expenses:Food:Snacks"}
        first_usage = {"Assets:Cash": object()}

        self.assertEqual(
            unused_open_accounts(opens, first_usage),
            ["Expenses:Food:Snacks"],
        )

    def test_treats_custom_account_values_as_usage(self):
        entries, errors, _ = loader.load_string(
            """
2026-01-01 open Expenses:Health:Supplements CNY
2026-01-01 custom "budget" Expenses:Health:Supplements "monthly" 150 CNY
"""
        )
        self.assertEqual(errors, [])

        self.assertIn(
            "Expenses:Health:Supplements",
            used_accounts(entries),
        )


if __name__ == "__main__":
    unittest.main()
