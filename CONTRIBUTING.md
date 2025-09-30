# Contributing to Vanta Bot

Thank you for your interest in contributing to Vanta Bot! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11+ (recommended: 3.11 or 3.12)
- Git
- Docker (optional, for containerized development)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/ChicoPanama/Vanta-Bot.git
   cd Vanta-Bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]  # Install development dependencies
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Development Workflow

### Running Tests

- **Unit tests only**: `pytest -q tests/unit`
- **Integration tests**: `pytest -q tests/integration -m "not live"`
- **All tests**: `pytest -q`

### Code Quality

We use several tools to maintain code quality:

- **Ruff**: Code formatting and linting
- **MyPy**: Type checking
- **Pre-commit**: Automated checks before commits

Run all checks:
```bash
ruff check .
mypy src/
pytest -q tests/unit
```

### Branching Model

- `main`: Protected branch, requires PR and CI approval
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- Hotfixes: `hotfix/description`

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass: `pytest -q tests/unit`
4. Run code quality checks: `ruff check . && mypy src/`
5. Commit your changes with descriptive messages
6. Push to your fork
7. Create a Pull Request

### Commit Message Format

Use conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

Example: `feat: add new trading strategy for high volatility markets`

## Code Style Guidelines

- Follow PEP 8 (enforced by Ruff)
- Use type hints for all functions
- Write docstrings for all public functions/classes
- Keep functions focused and small
- Use meaningful variable names

## Testing Guidelines

- Write unit tests for all new functionality
- Integration tests should be marked with `@pytest.mark.integration`
- Use fixtures for common test data
- Mock external dependencies in unit tests

## Security

- Never commit secrets or API keys
- Use environment variables for configuration
- Report security issues privately to dev@avantis.trading
- Do not open public issues for security vulnerabilities

## Getting Help

- Check existing issues and discussions
- Join our development Discord (link in README)
- Email: dev@avantis.trading

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
