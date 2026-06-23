FAVA_PYTHON ?= /Users/enmu/.local/pipx/venvs/fava/bin/python
FAVA ?= /Users/enmu/.local/bin/fava

.PHONY: validate fava

validate:
	$(FAVA_PYTHON) tools/validate_ledger.py

fava:
	$(FAVA) main.bean
