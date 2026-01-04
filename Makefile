.PHONY: mypy
mypy:
	mypy \
		--install-types --ignore-missing-imports \
		--check-untyped-defs --non-interactive \
		src/historical_racing_manager

.PHONY: flake8
flake8:
	flake8 \
		--count --max-complexity=18 --max-line-length=130 \
		--statistics \
		src/historical_racing_manager

.PHONY: pytest
pytest:
	pytest tests/
