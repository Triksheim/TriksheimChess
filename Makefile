PYTHON ?= python3

.PHONY: install run test clean

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py

test:
	$(PYTHON) ai_performance_tests.py

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache build dist *.egg-info
