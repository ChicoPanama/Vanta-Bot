install:
	pip install -r requirements.txt

fmt:
	black . && isort .

lint:
	ruff check .

typecheck:
	mypy src

sec:
	bandit -q -r src || true; safety check -r requirements.txt || true

test:
	pytest -q

all: fmt lint typecheck sec test