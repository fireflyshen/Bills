#!/usr/bin/env python3
"""Verify that a ledger migration changes account fields only."""

from __future__ import annotations

import argparse
import json
import re

from beancount import loader
from beancount.core.data import Open


ACCOUNT_RE = re.compile(
    r"^[A-Z][A-Za-z0-9-]*(?::[A-Z][A-Za-z0-9-]*)+$"
)
SOURCE_META_KEYS = frozenset({"filename", "lineno"})


def is_account(value) -> bool:
    return isinstance(value, str) and ACCOUNT_RE.fullmatch(value) is not None


def account_values(value) -> list[str]:
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


def verify_account(
    before: str,
    after: str,
    allowed_mapping,
    location: str,
) -> list[str]:
    if before == after:
        return []
    allowed = set(allowed_mapping.get(before, ()))
    if after in allowed:
        return []
    return [f"{location}: unapproved account change: {before} -> {after}"]


def verify_migration(
    before_entries,
    after_entries,
    allowed_mapping,
) -> list[str]:
    before = [entry for entry in before_entries if not isinstance(entry, Open)]
    after = [entry for entry in after_entries if not isinstance(entry, Open)]
    failures = []

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
                f"{type(old_entry).__name__} -> "
                f"{type(new_entry).__name__}"
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


def load_ledger(path: str):
    entries, errors, _ = loader.load_file(path)
    if errors:
        rendered = "\n".join(str(error) for error in errors)
        raise ValueError(f"{path} failed to load:\n{rendered}")
    return entries


def main() -> int:
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
