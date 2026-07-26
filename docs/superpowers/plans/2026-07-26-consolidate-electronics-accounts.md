# Electronics Account Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace four low-frequency electronics expense accounts with two durable categories while preserving every transaction amount.

**Architecture:** Move batteries into a broad household-supplies account. Combine mobile accessories, cables, chargers, and device-care purchases into one electronics-accessories account, then update Fane generation rules to emit only the new accounts.

**Tech Stack:** Beancount, YAML, shell validation

## Global Constraints

- Do not change transaction dates, metadata, payees, narrations, currencies, or amounts.
- Preserve the sum of the seven migrated postings at exactly `119.27 CNY`.
- Remove active references to the four retired account paths.
- Keep the historical migration document unchanged because it records an earlier migration.

---

### Task 1: Consolidate account definitions and historical postings

**Files:**
- Modify: `accounts/data/expenses.bean`
- Modify: `journal/2026/2026-01.bean`
- Modify: `journal/2026/2026-05.bean`
- Modify: `journal/2026/2026-06.bean`
- Modify: `journal/2026/2026-07.bean`

**Interfaces:**
- Consumes: Existing Beancount `open` directives and seven expense postings.
- Produces: `Expenses:Electronics:Accessories` and `Expenses:Household:Supplies`.

- [ ] **Step 1: Record the migration baseline**

Run:

```bash
rg -n 'Expenses:Electronics:(Batteries|CablesAndChargers|CareAndCleaning|MobileAccessories)' accounts journal
```

Expected: four account definitions and seven journal postings.

- [ ] **Step 2: Replace the four definitions with two accounts**

Use these exact accounts and Chinese comments:

```beancount
2026-01-08 open Expenses:Electronics:Accessories  ; 手机、充电及电子设备配件与养护用品
2026-01-08 open Expenses:Household:Supplies       ; 电池等低频家庭杂项用品
```

- [ ] **Step 3: Migrate the historical postings**

Map accounts without changing posting amounts:

```text
Expenses:Electronics:Batteries         -> Expenses:Household:Supplies
Expenses:Electronics:CablesAndChargers -> Expenses:Electronics:Accessories
Expenses:Electronics:CareAndCleaning   -> Expenses:Electronics:Accessories
Expenses:Electronics:MobileAccessories -> Expenses:Electronics:Accessories
```

### Task 2: Update generation rules and verify invariants

**Files:**
- Modify: `configs/bill.yaml`
- Test: `tools/validate_ledger.py`

**Interfaces:**
- Consumes: Fane rules that classify batteries, cables, and device cleaning.
- Produces: Rules that reference only the two consolidated accounts.

- [ ] **Step 1: Update YAML target accounts**

Apply the same four-to-two mapping to every `target-account` in `configs/bill.yaml`.

- [ ] **Step 2: Verify account coverage and migration amount**

Run repository searches to confirm that active account definitions, journals, and config contain no retired paths and that the seven migrated postings still total `119.27 CNY`.

- [ ] **Step 3: Verify syntax and ledger integrity**

Run:

```bash
git diff --check
make validate
```

Expected: no whitespace errors; ledger validation and subscription validation both pass.
