# Fane / Bills Configuration Regeneration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate `configs/bill.yaml` from the current Bills account tree and reviewed historical ALiPay/WeChat classifications so Fane produces correct current account paths and uses `FIXME` only when evidence is insufficient.

**Architecture:** Keep classification policy entirely in the existing Fane YAML schema. Use Bills Open directives as the account-name authority and existing source-tagged transactions as classification evidence; then verify the regenerated YAML with Fane's real parser, sample inputs, and both projects' test suites.

**Tech Stack:** YAML, Fane/Pydantic, Beancount, Python 3, unittest, ripgrep, jq

## Global Constraints

- Modify `configs/bill.yaml` only during implementation.
- Do not modify Fane source code or any Bills ledger directive.
- Every non-`FIXME` account in the YAML must have a current Bills Open directive.
- Keep `Assets:FIXME`, `Expenses:FIXME`, and `Income:FIXME` as generation-time review markers only.
- Prefer an explicit `FIXME` over an unproven classification.
- Preserve the current foreign-card repayment semantics and use `/Users/enmu/nexus/flowspace/Bills/main.bean`.
- Do not use the retired account paths listed in the approved design.
- Do not use category-only or day/amount-only expense classifications.

---

### Task 1: Establish the current account and behavior baseline

**Files:**
- Read: `accounts/data/assets.bean`
- Read: `accounts/data/liabilities.bean`
- Read: `accounts/data/income.bean`
- Read: `accounts/data/expenses.bean`
- Read: `journal/2025/*.bean`
- Read: `journal/2026/*.bean`
- Read: `configs/bill.yaml`
- Read: `/Users/enmu/nexus/ideaspace/projects/Fane/package/parser/rule_resolver.py`

**Interfaces:**
- Consumes: Current Open directives, existing source-tagged transactions, and Fane rule semantics.
- Produces: A verified set of permitted account paths and evidence-backed rule mappings for Task 2.

- [ ] **Step 1: Capture current YAML account references**

Run:

```bash
rg --no-filename -o \
  '(Assets|Liabilities|Equity|Income|Expenses):[A-Za-z0-9:-]+' \
  configs/bill.yaml | sort -u
```

Expected: the old configuration contains current accounts, `FIXME` sentinels,
and the known retired paths.

- [ ] **Step 2: Capture current Bills Open accounts**

Run:

```bash
rg --no-filename -o \
  '(Assets|Liabilities|Equity|Income|Expenses):[A-Za-z0-9:-]+' \
  accounts/data/*.bean | sort -u
```

Expected: every intended non-`FIXME` replacement is present.

- [ ] **Step 3: Confirm the current sample failure modes**

Run from Fane:

```bash
./.venv/bin/python main.py \
  --config /Users/enmu/nexus/flowspace/Bills/configs/bill.yaml \
  trans --provider alipay --source example/2.csv --format jsonl
```

Expected before regeneration: failure because the configured repayment ledger
uses `/root/.flow/account/main.bean`.

- [ ] **Step 4: Record the reviewed classification corrections**

Use the existing Bills transactions as the exact expected results:

```text
阿里云 + 关系型数据库RDS       -> Expenses:Technology:CloudInfrastructure:AliYun:RDS
阿里云 + 云服务器ECS          -> Expenses:Technology:CloudInfrastructure:AliYun:VPS
阿里云 + 阿里云服务购买       -> Expenses:Technology:CloudInfrastructure:AliYun:ServiceFees
JetBrains AI Pro              -> Expenses:Technology:AI:JetBrains:AIPro
中国移动信用卡退款             -> ICBC:8393 + Expenses:Communication:Mobile:Domestic
滴滴出行                      -> Expenses:Transport:RideHailing
南阳市公共交通集团             -> Expenses:Transport:PublicTransit
哈啰骑行 / 松果出行            -> Expenses:Transport:Micromobility
屏幕清洁湿巾                   -> Expenses:Electronics:CareAndCleaning
维生素C                       -> Expenses:Health:Supplements:VitaminsAndMinerals
梅溪路捷森文具商行             -> Expenses:Personal:Stationery
```

### Task 2: Regenerate the Fane YAML

**Files:**
- Modify: `configs/bill.yaml`

**Interfaces:**
- Consumes: The current accounts and reviewed mappings from Task 1.
- Produces: A Fane `Config`-compatible YAML file with ALiPay, WeChat, and foreign-card repayment rules.

- [ ] **Step 1: Replace the header and defaults**

Use:

```yaml
title: Bills
default-minus-account: Assets:FIXME
default-plus-account: Expenses:FIXME
default-currency: CNY
```

- [ ] **Step 2: Rebuild ALiPay rules in resolver-safe order**

Create these rule groups in this order:

```text
1. China Mobile ICBC-8393 refund rule with both accounts
2. Generic incoming-payment fallback to Income:FIXME
3. Reliable method rules for ICBC-8393, Alipay balance, and Yu'E Bao
4. Reviewed merchant/item expense rules
5. AliYun item-specific refinements
6. Explicit Yu'E Bao, bank-transfer, repayment, and refund transfer rules
```

The rule set must include the current accounts documented in Task 1 and retain
the reviewed food, haircut, electricity, power-bank, proxy, gift-card, iCloud,
and transport mappings from the existing configuration.

Do not recreate:

```yaml
- day-range: 8-11
  min-amount: 10.00
  max-amount: 20.00
```

- [ ] **Step 3: Rebuild WeChat rules in resolver-safe order**

Use `Assets:Cash:DigitalWallet:WeChat:Balance` for the generic incoming-payment
fallback. Retain and update reviewed method, food, proxy, logistics,
professional-development, haircut, family transfer, receivable, repayment,
and transport rules.

The transport mappings must be:

```text
滴滴出行                 -> Expenses:Transport:RideHailing
南阳市公共交通集团        -> Expenses:Transport:PublicTransit
哈啰骑行 / 松果出行       -> Expenses:Transport:Micromobility
```

- [ ] **Step 4: Correct foreign-card repayment configuration**

Use:

```yaml
foreign-credit-card-repayments:
  - trigger-minus-account: Assets:Investments:MoneyMarket:Alipay:YuEBao
    trigger-plus-account: Assets:Bank:ICBC:Checking:4931
    liability-account: Liabilities:CreditCard:ICBC:5788
    ledger-file: /Users/enmu/nexus/flowspace/Bills/main.bean
    currency: USD
    peer: 中国工商银行
    item: 信用卡提前还款
```

### Task 3: Verify the regenerated configuration

**Files:**
- Verify: `configs/bill.yaml`
- Verify: `/Users/enmu/nexus/ideaspace/projects/Fane/example/2.csv`
- Verify: `/Users/enmu/nexus/ideaspace/projects/Fane/example/3.xlsx`

**Interfaces:**
- Consumes: The regenerated YAML from Task 2.
- Produces: Evidence that the YAML parses, references only valid accounts, reproduces reviewed sample classifications, and does not break either project.

- [ ] **Step 1: Validate YAML and the Fane model**

Run from Fane:

```bash
./.venv/bin/python -c '
from package.config.config import Config
from package.config.init import load_config
path = "/Users/enmu/nexus/flowspace/Bills/configs/bill.yaml"
Config(**load_config(path))
print("Fane config valid.")
'
```

Expected: `Fane config valid.`

- [ ] **Step 2: Reject unknown non-FIXME accounts**

Extract account references from the YAML and current Open directives. Remove
the three permitted sentinels from the YAML set, then compare the sorted sets.

Expected: no YAML account appears outside the current Open-account set.

- [ ] **Step 3: Reject retired account paths**

Run:

```bash
rg -n \
  'CloudStorage:ICloud|Electronics:Accessories|Health:Supplements$|Household:Supplies|Family:Support:Transfers|Transport:Local' \
  configs/bill.yaml
```

Expected: no matches.

- [ ] **Step 4: Convert both Fane samples**

Run from Fane:

```bash
./.venv/bin/python main.py \
  --config /Users/enmu/nexus/flowspace/Bills/configs/bill.yaml \
  trans --provider alipay --source example/2.csv --format jsonl

./.venv/bin/python main.py \
  --config /Users/enmu/nexus/flowspace/Bills/configs/bill.yaml \
  trans --provider wechat --source example/3.xlsx --format jsonl
```

Expected: both exit 0.

- [ ] **Step 5: Inspect sample fallbacks and reviewed pairs**

Expected:

```text
JetBrains AI Pro -> Expenses:Technology:AI:JetBrains:AIPro
阿里云服务购买 -> Expenses:Technology:CloudInfrastructure:AliYun:ServiceFees
中国移动退款 -> Liabilities:CreditCard:ICBC:8393 + Expenses:Communication:Mobile:Domestic
reviewed sample entries containing FIXME -> 0
```

- [ ] **Step 6: Run Fane regression tests**

Run:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Run Bills validation**

Run:

```bash
make validate
```

Expected:

```text
Ledger validation passed.
errors=0
Subscription config valid.
```

- [ ] **Step 8: Check formatting and final status**

Run:

```bash
rg -n '[[:blank:]]+$' configs/bill.yaml
git diff --check
git status --short
```

Expected: no trailing whitespace, no tracked whitespace errors, and only the
intended untracked/modified `configs/bill.yaml` state remains.

