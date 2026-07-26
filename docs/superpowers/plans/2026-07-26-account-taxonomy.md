# Bills Account Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ambiguous and misclassified Bills accounts with the approved purpose-first taxonomy while proving that every historical posting amount, currency, date, and transaction balance is unchanged.

**Architecture:** Add two narrow safety layers before migrating data: unit-tested ledger-account hygiene checks in the normal validator, and a unit-tested before/after migration verifier that permits structurally typed account-field changes only. Then update explicit account opens and every ledger, budget, and subscription reference according to the approved mapping.

**Tech Stack:** Python 3, Beancount, unittest, Beanquery, JSON, Make

## Global Constraints

- Historical amounts, currencies, dates, signs, costs, prices, transaction balances, and posting counts must not change.
- Account paths may change only according to `docs/superpowers/specs/2026-07-26-account-taxonomy-design.md`.
- Do not infer Apple Gift Card denominations, exchange rates, or cost bases.
- Keep the 2,600 CNY electric vehicle as an expense under `Expenses:Transport:Vehicle:Purchase`.
- Preserve every budget amount, subscription amount, currency, billing day, and start/end date.
- Do not leave old and new account names mixed in the repository.
- Do not create merchant-specific accounts for one-time merchants.

---

### Task 1: Enforce clean account definitions

**Files:**
- Create: `tests/test_validate_ledger.py`
- Modify: `tools/validate_ledger.py`

**Interfaces:**
- Consumes: Existing `used_accounts(entries)` result and `opens` mapping in `main()`.
- Produces: `ambiguous_account_segments(accounts) -> dict[str, tuple[str, ...]]` and `unused_open_accounts(opens, first_usage) -> list[str]`.

- [ ] **Step 1: Write failing validator tests**

```python
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
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest tests/test_validate_ledger.py -v
```

Expected: import failure because `ambiguous_account_segments` and
`unused_open_accounts` do not exist.

- [ ] **Step 3: Implement the two minimal helpers**

Add to `tools/validate_ledger.py`:

```python
DISALLOWED_ACCOUNT_SEGMENTS = frozenset(
    {"fix", "fixme", "general", "other", "localservices"}
)


def ambiguous_account_segments(accounts) -> dict[str, tuple[str, ...]]:
    failures = {}
    for account in sorted(accounts):
        matches = tuple(
            segment
            for segment in account.split(":")
            if segment.casefold() in DISALLOWED_ACCOUNT_SEGMENTS
        )
        if matches:
            failures[account] = matches
    return failures


def unused_open_accounts(opens, first_usage) -> list[str]:
    return sorted(set(opens) - set(first_usage))
```

Integrate them in `main()` after `first_usage = used_accounts(entries)`:

```python
    unused_opens = unused_open_accounts(opens, first_usage)
    if unused_opens:
        failures.append("Open accounts without any ledger reference:")
        failures.extend(f"  - {account}" for account in unused_opens)

    ambiguous_accounts = ambiguous_account_segments(opens)
    if ambiguous_accounts:
        failures.append("Accounts contain ambiguous segments:")
        for account, segments in ambiguous_accounts.items():
            failures.append(f"  - {account}: {', '.join(segments)}")
```

- [ ] **Step 4: Run the unit tests and verify GREEN**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest tests/test_validate_ledger.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Run the validator and confirm the new checks catch the current ledger**

Run:

```bash
make validate
```

Expected: failure listing the approved-to-remove ambiguous and unused accounts.

### Task 2: Build an amount-preserving migration verifier

**Files:**
- Create: `tests/test_verify_account_migration.py`
- Create: `tools/verify_account_migration.py`
- Create: `docs/account-migration-2026-07.json`

**Interfaces:**
- Consumes: Before and after `main.bean` paths plus a JSON object mapping each old account to a list of permitted new accounts.
- Produces: `verify_migration(before_entries, after_entries, allowed_mapping) -> list[str]`; an empty list means every non-account field is identical and every account change is allowed.

- [ ] **Step 1: Write failing verifier tests**

Create tests that load two minimal ledgers with `beancount.loader.load_string`:

```python
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
        self.assertTrue(any("non-account fields changed" in item for item in failures))

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
        self.assertTrue(any("unapproved account change" in item for item in failures))

    def test_rejects_changed_fields_on_a_renamed_open(self):
        changed = AFTER.replace(
            "2026-01-01 open Expenses:Transport:RideHailing",
            "2025-12-31 open Expenses:Transport:RideHailing",
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
        self.assertTrue(any("open fields changed" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest tests/test_verify_account_migration.py -v
```

Expected: import failure because `tools.verify_account_migration` does not exist.

- [ ] **Step 3: Implement the minimal verifier**

Implement `tools/verify_account_migration.py`:

```python
import argparse
import json
import re

from beancount import loader
from beancount.core.data import Open


ACCOUNT_RE = re.compile(
    r"^[A-Z][A-Za-z0-9-]*(?::[A-Z][A-Za-z0-9-]*)+$"
)
SOURCE_META_KEYS = frozenset({"filename", "lineno"})


def is_account(value):
    return isinstance(value, str) and ACCOUNT_RE.fullmatch(value) is not None


def account_values(value):
    if is_account(value):
        return [value]
    if isinstance(value, dict):
        accounts = []
        for key, item in value.items():
            if key not in SOURCE_META_KEYS:
                accounts.extend(account_values(item))
        return accounts
    if hasattr(value, "_fields"):
        accounts = []
        for field in value._fields:
            accounts.extend(account_values(getattr(value, field)))
        return accounts
    if isinstance(value, (list, tuple, set, frozenset)):
        accounts = []
        for item in value:
            accounts.extend(account_values(item))
        return accounts
    return []


def normalized(value):
    if is_account(value):
        return "<ACCOUNT>"
    if isinstance(value, dict):
        return tuple(
            sorted(
                (key, normalized(item))
                for key, item in value.items()
                if key not in SOURCE_META_KEYS
            )
        )
    if hasattr(value, "_fields"):
        return (
            type(value).__name__,
            tuple(
                (field, normalized(getattr(value, field)))
                for field in value._fields
            ),
        )
    if isinstance(value, (list, tuple)):
        return tuple(normalized(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((normalized(item) for item in value), key=repr))
    return value


def verify_account(before, after, allowed_mapping, location):
    if before == after:
        return []
    allowed = set(allowed_mapping.get(before, ()))
    if after in allowed:
        return []
    return [f"{location}: unapproved account change: {before} -> {after}"]


def verify_opens(before_entries, after_entries, allowed_mapping):
    before_opens = {
        entry.account: entry
        for entry in before_entries
        if isinstance(entry, Open)
    }
    after_opens = {
        entry.account: entry
        for entry in after_entries
        if isinstance(entry, Open)
    }
    failures = []

    for account, old_open in sorted(before_opens.items()):
        new_open = after_opens.get(account)
        if new_open is not None:
            if normalized(old_open) != normalized(new_open):
                failures.append(f"{account}: open fields changed")
            continue
        if account not in allowed_mapping:
            failures.append(f"{account}: open was removed without approval")
            continue
        replacements = set(allowed_mapping[account])
        if replacements and not replacements.intersection(after_opens):
            failures.append(
                f"{account}: open was removed without an approved replacement"
            )

    for account, new_open in sorted(after_opens.items()):
        if account in before_opens:
            continue
        sources = [
            before_opens[source]
            for source, replacements in allowed_mapping.items()
            if source in before_opens and account in replacements
        ]
        if not sources:
            failures.append(f"{account}: open was added without approval")
            continue
        if not any(
            normalized(source_open) == normalized(new_open)
            for source_open in sources
        ):
            failures.append(f"{account}: open fields changed")

    return failures


def verify_migration(before_entries, after_entries, allowed_mapping):
    failures = verify_opens(
        before_entries,
        after_entries,
        allowed_mapping,
    )
    before = [entry for entry in before_entries if not isinstance(entry, Open)]
    after = [entry for entry in after_entries if not isinstance(entry, Open)]

    if len(before) != len(after):
        failures.append(
            "directive count changed outside Open directives: "
            f"{len(before)} -> {len(after)}"
        )
        return failures

    for index, (old_entry, new_entry) in enumerate(zip(before, after), start=1):
        location = f"directive #{index} ({old_entry.date})"
        if type(old_entry) is not type(new_entry):
            failures.append(
                f"{location}: directive type changed: "
                f"{type(old_entry).__name__} -> {type(new_entry).__name__}"
            )
            continue

        old_accounts = account_values(old_entry)
        new_accounts = account_values(new_entry)
        if len(old_accounts) != len(new_accounts):
            failures.append(
                f"{location}: account reference count changed: "
                f"{len(old_accounts)} -> {len(new_accounts)}"
            )
        else:
            for account_index, (old_account, new_account) in enumerate(
                zip(old_accounts, new_accounts),
                start=1,
            ):
                failures.extend(
                    verify_account(
                        old_account,
                        new_account,
                        allowed_mapping,
                        f"{location}, account #{account_index}",
                    )
                )

        if normalized(old_entry) != normalized(new_entry):
            failures.append(f"{location}: non-account fields changed")

    return failures


def load_ledger(path):
    entries, errors, _ = loader.load_file(path)
    if errors:
        rendered = "\n".join(str(error) for error in errors)
        raise ValueError(f"{path} failed to load:\n{rendered}")
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("before_main")
    parser.add_argument("after_main")
    parser.add_argument("mapping_json")
    args = parser.parse_args()

    with open(args.mapping_json, encoding="utf-8") as handle:
        raw_mapping = json.load(handle)
    allowed_mapping = {
        account: set(replacements)
        for account, replacements in raw_mapping.items()
    }

    failures = verify_migration(
        load_ledger(args.before_main),
        load_ledger(args.after_main),
        allowed_mapping,
    )
    if failures:
        print("Account migration verification failed.")
        for failure in failures:
            print(failure)
        return 1

    print("Account migration verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The CLI is:

```text
verify_account_migration.py BEFORE_MAIN AFTER_MAIN MAPPING_JSON
```

It loads both ledgers, fails on loader errors, prints every mismatch, and exits
1 on failure or prints `Account migration verification passed.` and exits 0.

Review hardening supersedes the illustrative implementation above:

- Recognize account fields structurally (`account`, `source_account`, and
  Beancount custom values whose `dtype` equals `beancount.core.account.TYPE`).
- Preserve account-shaped strings in payees, narrations, tags, links, and
  metadata so changing them still fails as a non-account change.
- Reject any mapped source that remains open or referenced unless its own path
  is explicitly included in its permitted replacement list.
- Verify Open date, currencies, booking method, and metadata independently
  from the account path.

- [ ] **Step 4: Run verifier tests and verify GREEN**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest tests/test_verify_account_migration.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Add the approved one-to-many mapping**

Create `docs/account-migration-2026-07.json`:

```json
{
  "Expenses:Electronics:Accessories": [
    "Expenses:Electronics:Batteries",
    "Expenses:Electronics:CablesAndChargers",
    "Expenses:Electronics:CareAndCleaning",
    "Expenses:Electronics:MobileAccessories"
  ],
  "Expenses:Entertainment:Subscriptions:DigitalMedia": [
    "Expenses:Entertainment:Subscriptions:Music"
  ],
  "Expenses:Family:Support:Transfers": [
    "Expenses:Family:Support"
  ],
  "Expenses:Financial:Fees": [
    "Expenses:Financial:BankFees"
  ],
  "Expenses:Health:Supplements": [
    "Expenses:Health:Supplements:Mixed",
    "Expenses:Health:Supplements:Protein",
    "Expenses:Health:Supplements:VitaminsAndMinerals"
  ],
  "Expenses:Household:Supplies": [
    "Expenses:Household:CleaningSupplies",
    "Expenses:Household:HomeFragrance",
    "Expenses:Household:Kitchenware",
    "Expenses:Personal:Stationery",
    "Expenses:Personal:Wellness:SleepAids",
    "Expenses:Professional:Resources"
  ],
  "Expenses:Services:LocalServices": [
    "Expenses:Services:Administrative"
  ],
  "Expenses:Services:General": [],
  "Expenses:Technology:AI:Google": [
    "Expenses:Technology:AI:Google:GoogleOnePro"
  ],
  "Expenses:Technology:AI:JetBrains": [
    "Expenses:Technology:AI:JetBrains:AIPro"
  ],
  "Expenses:Technology:AI:OpenAI": [
    "Expenses:Technology:AI:OpenAI:Codex"
  ],
  "Expenses:Technology:CloudStorage:ICloud": [
    "Expenses:Technology:CloudStorage:Apple:ICloud"
  ],
  "Expenses:Technology:Network:Proxy": [
    "Expenses:Food:Snacks",
    "Expenses:Technology:Network:Proxy",
    "Expenses:Transport:RideHailing"
  ],
  "Expenses:Technology:Services:Office": [
    "Expenses:Technology:Software:Productivity"
  ],
  "Expenses:Technology:Services:Other": [
    "Expenses:Communication:Mobile:ServiceFees",
    "Expenses:Technology:DigitalGoods:GiftCards"
  ],
  "Expenses:Technology:Software:Applications": [
    "Expenses:Technology:DigitalGoods:GiftCards",
    "Expenses:Technology:Software:Applications"
  ],
  "Expenses:Technology:Subscriptions:General": [
    "Expenses:Technology:Network:Proxy"
  ],
  "Expenses:Transport:Local": [
    "Expenses:Transport:Micromobility",
    "Expenses:Transport:PublicTransit",
    "Expenses:Transport:RideHailing",
    "Expenses:Transport:Vehicle:Purchase"
  ],
  "Income:Interest:Bank:ICBC": [],
  "Income:Interest:Investment": []
}
```

Unchanged mapped source accounts are valid only when their own path is
explicitly included in the replacement list.

- [ ] **Step 6: Run all unit tests**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest discover -s tests -v
```

Expected: 11 tests pass.

### Task 3: Migrate account opens and historical postings

**Files:**
- Modify: `accounts/data/expenses.bean`
- Modify: `accounts/data/income.bean`
- Modify: `journal/2025/2025-11.bean`
- Modify: `journal/2025/2025-12.bean`
- Modify: `journal/2026/2026-01.bean`
- Modify: `journal/2026/2026-02.bean`
- Modify: `journal/2026/2026-03.bean`
- Modify: `journal/2026/2026-04.bean`
- Modify: `journal/2026/2026-05.bean`
- Modify: `journal/2026/2026-06.bean`
- Modify: `journal/2026/2026-07.bean`
- Modify: `journal/2025/income.bean`
- Modify: `journal/2026/income.bean`

**Interfaces:**
- Consumes: Approved taxonomy and `docs/account-migration-2026-07.json`.
- Produces: Explicit open directives and historical postings using only the new taxonomy.

- [ ] **Step 1: Create a read-only baseline snapshot**

Run:

```bash
BASELINE_DIR=$(mktemp -d /tmp/bills-account-baseline.XXXXXX)
git archive HEAD | tar -x -C "$BASELINE_DIR"
```

Keep `BASELINE_DIR` for Task 5. Do not modify it.

- [ ] **Step 2: Replace account opens**

Rewrite `accounts/data/expenses.bean` to match the approved tree. Preserve
source open dates for global renames and use source-account open dates for
splits. Remove:

```text
Expenses:Services:General
Expenses:Technology:Subscriptions:General
Income:Interest:Investment
Income:Interest:Bank:ICBC
```

- [ ] **Step 3: Apply global historical renames**

Replace every occurrence of the nine global mappings in the design, including
AI product paths and Apple iCloud. Do not change surrounding transaction text.

- [ ] **Step 4: Apply transaction-specific splits**

Use date, payee, narration, and current account together to make each split.
Match the exact totals in the design:

```text
Transport: 45.85 RideHailing; 1.00 PublicTransit;
           13.90 Micromobility; 2600.00 Vehicle:Purchase
Household: 19.84 Stationery; 34.80 SleepAids; 35.00 Resources;
           55.00 Kitchenware; 30.30 CleaningSupplies;
           38.40 HomeFragrance
Electronics: 17.17 MobileAccessories; 27.00 Batteries;
             36.69 CareAndCleaning; 38.41 CablesAndChargers
Supplements: 174.40 Mixed; 87.03 Protein;
             267.92 VitaminsAndMinerals
```

Move the 2026-07-11 snack and two July Didi postings out of Proxy.

- [ ] **Step 5: Run the migration verifier**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python \
  tools/verify_account_migration.py \
  "$BASELINE_DIR/main.bean" \
  main.bean \
  docs/account-migration-2026-07.json
```

Expected: `Account migration verification passed.`

- [ ] **Step 6: Query target totals**

Run Beanquery for all newly split accounts and confirm the exact totals from
the design. Any mismatch must be corrected by account classification only.

### Task 4: Update budgets, subscriptions, policy, and validation

**Files:**
- Modify: `budgets/data/2026.bean`
- Modify: `plugins/auto_subscriptions.json`
- Modify: `docs/accounting-policy.md`

**Interfaces:**
- Consumes: New explicit account opens from Task 3.
- Produces: No stale account references in generated or reporting inputs.

- [ ] **Step 1: Update budget account paths without changing values**

Apply the AI global renames, then use these exact aggregate-budget mappings:

```text
Expenses:Health:Supplements
  -> Expenses:Health:Supplements:VitaminsAndMinerals
Expenses:Household:Supplies
  -> Expenses:Household:CleaningSupplies
Expenses:Transport:Local
  -> Expenses:Transport:RideHailing
Expenses:Technology:Subscriptions:General
  -> Expenses:Technology:Network:Proxy
```

Preserve all dates, recurrence strings, amounts, and currencies.

- [ ] **Step 2: Update subscription debit accounts without changing terms**

Change only `debit_account`:

```json
"Expenses:Technology:AI:Google:GoogleOnePro"
"Expenses:Technology:AI:OpenAI:Codex"
```

Keep IDs, status, type, interval, payee, narration, credit accounts, amounts,
currencies, billing days, and dates byte-for-byte unchanged.

- [ ] **Step 3: Update the accounting policy**

Document the purpose-first rule, 3-to-5-level target, stable-provider
exception, disallowed ambiguous segments, and migration verifier requirement
for future historical account refactors.

- [ ] **Step 4: Run all validation**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest discover -s tests -v
make validate
git diff --check
```

Expected: 11 unit tests pass; ledger validation reports 0 errors; subscription
config is valid; Git reports no whitespace errors.

### Task 5: Prove the migration and commit

**Files:**
- Verify all modified files from Tasks 1 through 4.

**Interfaces:**
- Consumes: Baseline snapshot from Task 3 and completed migration.
- Produces: Auditable evidence that the approved taxonomy is complete and all numeric ledger data is unchanged.

- [ ] **Step 1: Run the full before/after verifier again**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python \
  tools/verify_account_migration.py \
  "$BASELINE_DIR/main.bean" \
  main.bean \
  docs/account-migration-2026-07.json
```

Expected: `Account migration verification passed.`

- [ ] **Step 2: Confirm no stale or ambiguous account remains**

Run:

```bash
rg -n -i 'fixme|Expenses:Fix(?:\s|$)|:General(?:\s|$)|:Other(?:\s|$)|:LocalServices(?:\s|$)' \
  accounts budgets journal accruals assertion init plugins main.bean
```

Expected: no matches.

- [ ] **Step 3: Compare root totals by currency**

Run the approved Beanquery root-total query against the baseline and current
ledger. Assets, Liabilities, Equity, Income, and Expenses totals must match
exactly for CNY, USD, and GBP.

- [ ] **Step 4: Run the final verification suite**

Run:

```bash
/Users/enmu/.local/pipx/venvs/fava/bin/python -m unittest discover -s tests -v
make validate
git diff --check
git status --short
```

Read every output and stop if any command fails.

- [ ] **Step 5: Commit the implementation**

```bash
git add \
  accounts budgets docs journal plugins tools tests \
  accruals assertion init
git commit -m "refactor: 重构账本账户体系"
```
