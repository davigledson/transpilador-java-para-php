PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
FILE ?= examples/Banco.java
OUT ?= build/demo

.PHONY: install test diff project demo transpile check lint clean

install:
	python3 -m venv .venv
	$(PIP) install -e '.[dev]'

test:
	$(PYTHON) -m pytest -q

diff:
	$(PYTHON) scripts/diff_test.py

project:
	$(PYTHON) scripts/project_test.py

check: test diff project lint

lint:
	$(PYTHON) -m compileall -q src
	for f in runtime/php/*.php; do php -l "$$f" || exit 1; done

demo:
	$(PYTHON) scripts/diff_test.py $(FILE)

transpile:
	$(PYTHON) -m transpilador $(FILE) -o $(OUT)

clean:
	rm -rf build .pytest_cache
