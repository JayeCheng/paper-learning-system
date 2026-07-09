PYTHON ?= python

.PHONY: install test lint daily backfill export sync-notion

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m compileall src scripts tests

daily:
	$(PYTHON) scripts/run_daily.py

backfill:
	$(PYTHON) scripts/backfill_classics.py

export:
	$(PYTHON) scripts/export_to_csv.py

sync-notion:
	$(PYTHON) scripts/sync_notion.py
