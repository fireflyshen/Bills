# Fane / Bills Configuration Regeneration Design

**Date:** 2026-07-26

## Goal

Regenerate `configs/bill.yaml` so Fane produces account references that match
the current Bills account tree as accurately as the available historical
evidence permits.

Accuracy has priority over coverage. A transaction may fall through to a
visible `FIXME` sentinel when the available fields do not support a reliable
classification; it must not be assigned to a plausible but unproven account.

## Scope

This change modifies `configs/bill.yaml` only.

It does not:

- modify Fane source code;
- modify historical Bills directives, amounts, currencies, dates, or balances;
- add `Fix` or `FIXME` accounts to Bills;
- invent accounts that are not open in the current Bills ledger;
- infer classifications solely from broad payment categories.

## Sources of Truth

The regenerated configuration uses these sources in descending priority:

1. Current explicit account opens under `accounts/data/`.
2. Existing ALiPay and WeChat transactions in Bills whose account
   classifications have already been reviewed.
3. Fane's actual rule schema, matching behavior, refund behavior, and sample
   bill files.
4. Existing `configs/bill.yaml` rules only when their semantics remain
   supported by the first three sources.

## Fallback Policy

Fane retains these sentinels:

```yaml
default-minus-account: Assets:FIXME
default-plus-account: Expenses:FIXME
```

Generic incoming-payment rules may use `Income:FIXME`.

These are generation-time review markers, not Bills accounts. Every other
account referenced by the YAML must have a current Open directive in Bills.
Any generated entry containing `FIXME` requires manual classification before
it can be imported into the validated ledger.

## Rule Design

### Ordering

Fane normally evaluates every matching rule from top to bottom, allowing later
rules to refine earlier ones. Refunds are different: the resolver returns
after the first matching rule.

Rules therefore use this order:

1. Combined refund rules that set both method and target accounts.
2. Generic incoming-payment fallback rules.
3. Broad, reliable payment-method mappings.
4. Stable merchant and item mappings.
5. More specific compound rules that refine ambiguous merchants.
6. Explicit transfer rules.

### Classification Standard

- Use a merchant rule only when its historical transactions consistently map
  to one current account.
- Use merchant plus item, method, type, status, or amount when the merchant
  has multiple legitimate classifications.
- Prefer item rules for masked or unstable merchant names when the item
  meaning is specific.
- Do not classify by broad categories such as `餐饮美食` or `日用百货`.
- Remove the old day-of-month and amount-only proxy heuristic because it can
  capture unrelated purchases.
- Keep stable method mappings for known bank cards, wallet balances, and
  Yu'E Bao.

### Required Current-Tree Migrations

The regenerated rules use the current accounts, including:

```text
Expenses:Technology:CloudStorage:Apple:ICloud
Expenses:Electronics:CareAndCleaning
Expenses:Health:Supplements:VitaminsAndMinerals
Expenses:Personal:Stationery
Expenses:Family:Support
Expenses:Transport:RideHailing
Expenses:Transport:PublicTransit
Expenses:Transport:Micromobility
```

No rule may retain these retired paths:

```text
Expenses:Technology:CloudStorage:ICloud
Expenses:Electronics:Accessories
Expenses:Health:Supplements
Expenses:Household:Supplies
Expenses:Family:Support:Transfers
Expenses:Transport:Local
```

### Known Precision Corrections

- `阿里云` is refined by item into RDS, VPS, or ServiceFees.
- `JetBrains AI Pro` maps to
  `Expenses:Technology:AI:JetBrains:AIPro`.
- China Mobile credit-card refunds set both
  `Liabilities:CreditCard:ICBC:8393` and
  `Expenses:Communication:Mobile:Domestic` in one rule.
- Didi, public transit, and shared-bike merchants map to separate transport
  leaves.
- Screen-cleaning products, vitamins, and stationery map to their current
  concrete leaves.
- The WeChat generic income fallback uses the WeChat balance, not the Alipay
  balance.

## Foreign Credit-Card Repayment

The repayment configuration points to the actual ledger:

```text
/Users/enmu/nexus/flowspace/Bills/main.bean
```

Its trigger accounts, liability account, currency, peer, and item must remain
consistent with the existing Bills repayment entries.

## Verification

The completed YAML must pass all of the following:

1. YAML parsing and Fane `Config` model validation.
2. Every non-`FIXME` account reference exists in current Bills Open
   directives.
3. No retired account path remains.
4. Fane's ALiPay and WeChat sample bills convert successfully.
5. Sample transactions that already exist in Bills resolve to the same account
   pairs, including AliYun service fees and the China Mobile refund.
6. No sample transaction that already has a reviewed Bills classification
   falls through to `FIXME`.
7. Fane's regression test suite passes.
8. `make validate` passes in Bills.
9. `git diff --check` reports no whitespace errors.

