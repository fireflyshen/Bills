#!/usr/bin/env python3
"""Verify that a ledger migration changes account fields only."""

from __future__ import annotations

import argparse
import json

from beancount import loader
from beancount.core.account import TYPE as ACCOUNT_TYPE
from beancount.core.data import Open


ACCOUNT_FIELDS = frozenset({"account", "source_account"})
SOURCE_META_KEYS = frozenset({"filename", "lineno"})


def is_custom_account_value(value) -> bool:
    return (
        getattr(value, "dtype", None) == ACCOUNT_TYPE
        and hasattr(value, "value")
    )


def account_values(value) -> list[str]:
    if isinstance(value, dict):
        return []
    if hasattr(value, "_fields"):
        if is_custom_account_value(value):
            return [value.value]
        accounts = []
        for field in value._fields:
            item = getattr(value, field)
            if field in ACCOUNT_FIELDS and isinstance(item, str):
                accounts.append(item)
            else:
                accounts.extend(account_values(item))
        return accounts
    if isinstance(value, (list, tuple, set, frozenset)):
        accounts = []
        for item in value:
            accounts.extend(account_values(item))
        return accounts
    return []


def normalized(value):
    if isinstance(value, dict):
        return tuple(
            sorted(
                (key, normalized(item))
                for key, item in value.items()
                if key not in SOURCE_META_KEYS
            )
        )
    if hasattr(value, "_fields"):
        custom_account_value = is_custom_account_value(value)
        return (
            type(value).__name__,
            tuple(
                (
                    field,
                    "<ACCOUNT>"
                    if field in ACCOUNT_FIELDS
                    or (custom_account_value and field == "value")
                    else normalized(getattr(value, field)),
                )
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
        if (
            before in allowed_mapping
            and before not in set(allowed_mapping[before])
        ):
            return [f"{location}: retired account remains: {before}"]
        return []
    allowed = set(allowed_mapping.get(before, ()))
    if after in allowed:
        return []
    return [f"{location}: unapproved account change: {before} -> {after}"]


def verify_opens(
    before_entries,
    after_entries,
    allowed_mapping,
) -> list[str]:
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
            if (
                account in allowed_mapping
                and account not in set(allowed_mapping[account])
            ):
                failures.append(f"{account}: retired account remains open")
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


def verify_migration(
    before_entries,
    after_entries,
    allowed_mapping,
) -> list[str]:
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
