#!/usr/bin/env bash
set -euo pipefail

echo "Setting up CI environment..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install flake8 black isort mypy bandit safety pytest-cov pytest-benchmark

echo "Running linters..."
black --check .
isort --profile black --check-only .
flake8 .
mypy --ignore-missing-imports src tests

echo "Running security scans..."
bandit -r src -ll || true
safety check -r requirements.txt --full-report || true

echo "Running tests with coverage..."
pytest -q --cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=90

echo "Done."

