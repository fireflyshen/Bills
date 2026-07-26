import unittest

from tools.validate_ledger import (
    ambiguous_account_segments,
    unused_open_accounts,
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


if __name__ == "__main__":
    unittest.main()
