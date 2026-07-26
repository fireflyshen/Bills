import unittest

from beancount import loader

from tools.verify_account_migration import verify_migration


def entries(source):
    loaded, errors, _ = loader.load_string(source)
    if errors:
        raise AssertionError(errors)
    return loaded


BEFORE = """
2026-01-01 open Assets:Cash CNY
2026-01-01 open Expenses:Transport:Local CNY
2026-01-02 * "Didi" "Ride"
  Expenses:Transport:Local  10.00 CNY
  Assets:Cash             -10.00 CNY
"""

AFTER = """
2026-01-01 open Assets:Cash CNY
2026-01-01 open Expenses:Transport:RideHailing CNY
2026-01-02 * "Didi" "Ride"
  Expenses:Transport:RideHailing  10.00 CNY
  Assets:Cash                    -10.00 CNY
"""


class MigrationVerifierTests(unittest.TestCase):
    def test_accepts_an_allowed_account_only_change(self):
        failures = verify_migration(
            entries(BEFORE),
            entries(AFTER),
            {
                "Expenses:Transport:Local": {
                    "Expenses:Transport:RideHailing"
                }
            },
        )

        self.assertEqual(failures, [])

    def test_rejects_a_changed_amount(self):
        changed = AFTER.replace("  10.00 CNY", "  11.00 CNY").replace(
            "-10.00 CNY",
            "-11.00 CNY",
        )
        failures = verify_migration(
            entries(BEFORE),
            entries(changed),
            {
                "Expenses:Transport:Local": {
                    "Expenses:Transport:RideHailing"
                }
            },
        )

        self.assertTrue(
            any("non-account fields changed" in item for item in failures)
        )

    def test_rejects_an_unapproved_account_change(self):
        changed = AFTER.replace("RideHailing", "AirTravel")
        failures = verify_migration(
            entries(BEFORE),
            entries(changed),
            {
                "Expenses:Transport:Local": {
                    "Expenses:Transport:RideHailing"
                }
            },
        )

        self.assertTrue(
            any("unapproved account change" in item for item in failures)
        )


if __name__ == "__main__":
    unittest.main()
