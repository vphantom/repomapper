.PHONY: build clean format help lint prep test

PY_SRC := scripts/build_single.py $(wildcard src/repomapper/*.py src/repomapper/handlers/*.py)

help:
	@echo "Available targets:"
	@echo "  help         - print this help"
	@echo "  format       - format with Black"
	@echo "  lint         - lint with Flake8"
	@echo "  test         - run pytest"
	@echo "  prep         - format, lint, and test"
	@echo "  build        - build stand-alone 'repomapper'"
	@echo "  clean        - clean up build artifacts except 'repomapper'"

repomapper: $(PY_SRC)
	PYTHONPATH=src python3 scripts/build_single.py

build: repomapper

format:
	black .

lint:
	flake8 setup.py src/ tests/

test:
	PYTHONPATH=src pytest -v

# Unfortunately, depending on the other rules doesn't seem to guarantee running
# order, so we're duplicating them instead.
prep:
	black .
	flake8 setup.py src/ tests/
	PYTHONPATH=src pytest

clean:
	rm -fr .pytest_cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
