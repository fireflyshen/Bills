FAVA_PYTHON ?= /Users/enmu/.local/pipx/venvs/fava/bin/python
FAVA ?= /Users/enmu/.local/bin/fava
SUBSCRIPTION_MONTH ?= $(shell date +%Y-%m)

.PHONY: validate subscriptions-dry-run subscriptions fava

validate:
	$(FAVA_PYTHON) tools/validate_ledger.py
	$(FAVA_PYTHON) tools/generate_subscriptions.py --check

subscriptions-dry-run:
	$(FAVA_PYTHON) tools/generate_subscriptions.py --month $(SUBSCRIPTION_MONTH)

subscriptions:
	$(FAVA_PYTHON) tools/generate_subscriptions.py --month $(SUBSCRIPTION_MONTH) --write

fava:
	$(FAVA) main.bean
