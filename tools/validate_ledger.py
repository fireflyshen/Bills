#!/usr/bin/env python3
"""Validate structural quality for this Beancount ledger.

Run with the same Python environment that provides Fava/Beancount, for example:

    /Users/enmu/.local/pipx/venvs/fava/bin/python tools/validate_ledger.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from beancount import loader
from beancount.core.data import Balance, Close, Custom, Open, Pad, Transaction


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "main.bean"

REQUIRED_OPERATING_CURRENCIES = {"CNY", "USD", "GBP"}

REQUIRED_METADATA = {
    "Assets:Bank": {"institution", "account_type"},
    "Assets:Cash:DigitalWallet": {"platform", "liquidity"},
    "Assets:StoredValue": {"platform", "account_type"},
    "Assets:Investments:MoneyMarket": {"product"},
    "Assets:Receivables": {"counterparty"},
    "Liabilities:CreditCard": {"institution", "account_type", "last4"},
    "Liabilities:ConsumerCredit": {"platform", "product"},
    "Liabilities:AccruedExpenses": {"domain", "recognition"},
    "Income:Employment": {"income_type"},
    "Income:Family": {"income_type"},
    "Income:Rebates": {"income_type"},
}


def account_values(custom: Custom) -> set[str]:
    accounts = set()
    for value in custom.values:
        if getattr(value, "dtype", None) == "account":
            accounts.add(value.value)
    return accounts


def used_accounts(entries) -> dict[str, object]:
    first_usage = {}
    for entry in entries:
        accounts = set()
        if isinstance(entry, Transaction):
            accounts.update(posting.account for posting in entry.postings)
        elif isinstance(entry, Balance):
            accounts.add(entry.account)
        elif isinstance(entry, Pad):
            accounts.add(entry.account)
            accounts.add(entry.source_account)
        elif isinstance(entry, Close):
            accounts.add(entry.account)
        elif isinstance(entry, Custom):
            accounts.update(account_values(entry))

        for account in accounts:
            first_usage.setdefault(account, entry)
    return first_usage


def commodities_used(entries) -> set[str]:
    commodities = set()
    for entry in entries:
        if not isinstance(entry, Transaction):
            if isinstance(entry, Balance):
                commodities.add(entry.amount.currency)
            continue
        for posting in entry.postings:
            if posting.units is not None:
                commodities.add(posting.units.currency)
            if posting.cost is not None:
                commodities.add(posting.cost.currency)
            if posting.price is not None:
                commodities.add(posting.price.currency)
    return commodities


def metadata_required_for(account: str) -> set[str]:
    required = set()
    for prefix, keys in REQUIRED_METADATA.items():
        if account == prefix or account.startswith(prefix + ":"):
            required.update(keys)
    return required


def main() -> int:
    entries, errors, options = loader.load_file(str(LEDGER))
    failures = []

    if errors:
        failures.append(f"Beancount loader returned {len(errors)} error(s).")
        failures.extend(str(error) for error in errors[:20])

    opens = {entry.account: entry for entry in entries if isinstance(entry, Open)}
    first_usage = used_accounts(entries)

    missing_opens = sorted(set(first_usage) - set(opens))
    if missing_opens:
        failures.append("Used accounts without explicit open directives:")
        failures.extend(f"  - {account}" for account in missing_opens)

    late_opens = []
    for account, first_entry in first_usage.items():
        open_entry = opens.get(account)
        if open_entry and open_entry.date > first_entry.date:
            late_opens.append((account, open_entry.date, first_entry.date))
    if late_opens:
        failures.append("Accounts opened after their first usage:")
        failures.extend(
            f"  - {account}: open {open_date}, first use {first_date}"
            for account, open_date, first_date in late_opens
        )

    operating_currencies = set(options.get("operating_currency", []))
    missing_required = sorted(REQUIRED_OPERATING_CURRENCIES - operating_currencies)
    if missing_required:
        failures.append(
            "Missing required operating currencies: " + ", ".join(missing_required)
        )

    unreported_commodities = sorted(commodities_used(entries) - operating_currencies)
    if unreported_commodities:
        failures.append(
            "Commodities used but not configured as operating currencies: "
            + ", ".join(unreported_commodities)
        )

    metadata_failures = defaultdict(list)
    for account, open_entry in sorted(opens.items()):
        required = metadata_required_for(account)
        missing = sorted(required - set(open_entry.meta))
        if missing:
            metadata_failures[account].extend(missing)
    if metadata_failures:
        failures.append("Accounts missing required metadata:")
        for account, missing in metadata_failures.items():
            failures.append(f"  - {account}: {', '.join(missing)}")

    if failures:
        print("Ledger validation failed.")
        for failure in failures:
            print(failure)
        return 1

    print("Ledger validation passed.")
    print(f"entries={len(entries)} opens={len(opens)} errors=0")
    print("operating_currencies=" + ",".join(sorted(operating_currencies)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
