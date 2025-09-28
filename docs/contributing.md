# Contributing

Thanks for considering a contribution! This repo follows a “small, safe, and tested” philosophy.

Guidelines
- Discuss significant changes in an issue/PR before implementation.
- Keep changes focused; avoid unrelated refactors in the same PR.
- Add or update tests for any behavior change.
- Update documentation (README, docs/, env.example) if user‑facing behavior changes.

Local Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Style & Tooling
- Formatting: black + isort (see `Makefile` targets)
- Linting: ruff, mypy (see `pyproject.toml`)
- Security checks: bandit, safety (best‑effort)

Submitting
1. Fork and create a feature branch.
2. Make your changes and add tests.
3. Run `make all` to format, lint, type‑check, and test.
4. Open a PR with a concise description and rationale.

Thank you!
