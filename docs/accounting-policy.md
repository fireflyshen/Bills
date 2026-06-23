# Accounting Policy

This ledger is optimized for personal finance analysis in Fava while preserving
plain Beancount compatibility.

## Core Principles

- Data correctness comes first: do not rewrite historical amounts or counterparties
  unless the source record was wrong.
- Account paths should be stable. Prefer adding a child account over renaming a
  heavily used existing account.
- Use account metadata for institution, platform, last four digits, product names
  and recognition policy. This keeps account names readable while preserving
  analytical detail.
- Keep CNY as the base household currency. USD and GBP are operating currencies
  because they are recurring subscription and card currencies.

## Account Naming

Assets:

`Assets:<class>:<institution-or-platform>:<product-or-purpose>[:identifier]`

Liabilities:

`Liabilities:<class>:<institution-or-domain>:<product-or-purpose>[:identifier]`

Income:

`Income:<source-class>:<source-or-platform>[:product-or-identifier]`

Expenses:

`Expenses:<domain>:<category>[:vendor-or-purpose]`

## Classification Rules

- Bank checking and time deposits stay under `Assets:Bank`.
- Alipay and WeChat spendable balances stay under `Assets:Cash:DigitalWallet`.
- Platform prepaid balances, such as Apple ID credit, stay under
  `Assets:StoredValue`.
- Money-market funds stay under `Assets:Investments:MoneyMarket`, even when they
  are liquid enough for daily cash management.
- Credit cards stay under `Liabilities:CreditCard` and should carry institution,
  account type and last-four metadata.
- Recognized but unpaid family obligations stay under
  `Liabilities:AccruedExpenses`. Cash payment should reduce the payable rather
  than duplicate the monthly expense.
- Recurring technology services should be classified at the service family level
  when it helps budgets, for example `Technology:AI`, `CloudInfrastructure`,
  `CloudStorage`, `DeveloperTools`, `Network` and `Domains`.

## Extension Checklist

Before adding a new account:

1. Check whether an existing child account already represents the same economic
   substance.
2. Add the narrowest useful account path.
3. Add metadata for institution or platform, product, last four digits and any
   recognition policy.
4. Use an opening date no later than the first transaction date.
5. Run `make validate` and keep the ledger at zero structural errors.
