import unittest
from datetime import date

from beancount import loader

from tools.query_period import query_entries
from tools.query_period_server import execute_query


LEDGER = """
2026-01-01 open Assets:Bank:Checking CNY
2026-01-01 open Assets:Cash:Wallet CNY
2026-01-01 open Assets:Prepaid:Insurance CNY
2026-01-01 open Liabilities:CreditCard CNY
2026-01-01 open Liabilities:AccruedExpenses CNY
2026-01-01 open Income:Salary CNY
2026-01-01 open Expenses:Food CNY
2026-01-01 open Expenses:Insurance CNY

2026-07-27 * "Employer" "Salary"
  Assets:Bank:Checking       1000.00 CNY
  Income:Salary             -1000.00 CNY

2026-07-28 * "Shop" "Food"
  Expenses:Food                80.00 CNY
  Liabilities:CreditCard      -80.00 CNY

2026-07-29 * "Shop" "Refund"
  Liabilities:CreditCard       20.00 CNY
  Expenses:Food               -20.00 CNY

2026-07-30 * "Bank" "Move money"
  Assets:Cash:Wallet          200.00 CNY
  Assets:Bank:Checking       -200.00 CNY

2026-07-31 * "Bank" "Pay card"
  Liabilities:CreditCard       60.00 CNY
  Assets:Bank:Checking        -60.00 CNY

2026-08-01 * "Insurance" "Annual premium"
  Assets:Prepaid:Insurance    120.00 CNY
  Assets:Bank:Checking       -120.00 CNY

2026-08-02 * "Insurance" "Monthly recognition"
  Expenses:Insurance           10.00 CNY
  Assets:Prepaid:Insurance    -10.00 CNY

2026-08-03 * "Later" "Outside range"
  Expenses:Food                 5.00 CNY
  Assets:Cash:Wallet           -5.00 CNY
"""


class QueryPeriodTests(unittest.TestCase):
    def setUp(self):
        self.entries, self.errors, _ = loader.load_string(LEDGER)
        self.assertEqual(self.errors, [])

    def test_summarizes_income_expenses_refunds_and_transfers(self):
        result = query_entries(
            self.entries,
            date(2026, 7, 27),
            date(2026, 8, 2),
        )

        self.assertEqual(result["statistics"]["transaction_count"], 7)
        self.assertEqual(
            result["statistics"]["transaction_kinds"],
            {
                "asset_transfer": 2,
                "expense": 2,
                "income": 1,
                "liability_settlement": 1,
                "refund": 1,
            },
        )
        self.assertEqual(result["totals"]["income"]["net"], {"CNY": "1000.00"})
        self.assertEqual(result["totals"]["expenses"]["gross"], {"CNY": "90.00"})
        self.assertEqual(result["totals"]["expenses"]["refunds"], {"CNY": "20.00"})
        self.assertEqual(result["totals"]["expenses"]["net"], {"CNY": "70.00"})
        self.assertEqual(
            result["expenses_by_account"],
            {
                "Expenses:Food": {"CNY": "60.00"},
                "Expenses:Insurance": {"CNY": "10.00"},
            },
        )

    def test_credit_card_payment_and_prepayment_are_not_expenses(self):
        result = query_entries(
            self.entries,
            date(2026, 7, 30),
            date(2026, 8, 1),
        )

        self.assertEqual(result["totals"]["expenses"]["net"], {})
        self.assertEqual(
            [transaction["kind"] for transaction in result["transactions"]],
            ["asset_transfer", "liability_settlement", "asset_transfer"],
        )

    def test_truncates_details_without_changing_totals(self):
        result = query_entries(
            self.entries,
            date(2026, 7, 27),
            date(2026, 8, 2),
            max_transactions=2,
        )

        self.assertEqual(result["statistics"]["transaction_count"], 7)
        self.assertEqual(result["statistics"]["returned_transaction_count"], 2)
        self.assertTrue(result["statistics"]["truncated"])
        self.assertEqual(result["totals"]["expenses"]["net"], {"CNY": "70.00"})
        self.assertIn("totals include all 7 transactions", result["warnings"][0])

    def test_http_query_validation_rejects_non_date_input(self):
        with self.assertRaisesRegex(Exception, "expected YYYY-MM-DD"):
            execute_query(
                {
                    "start_date": "2026-07-27; rm -rf /",
                    "end_date": "2026-08-02",
                }
            )


if __name__ == "__main__":
    unittest.main()
