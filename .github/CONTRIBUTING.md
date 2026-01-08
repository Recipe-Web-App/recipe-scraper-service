# Contributing to Recipe Scraper Service

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing
to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Security](#security)

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report
unacceptable behavior through the project's issue tracker.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/recipe-scraper-service.git
   cd recipe-scraper-service
   ```

3. **Add upstream remote**:

   ```bash
   git remote add upstream https://github.com/Recipe-Web-App/recipe-scraper-service.git
   ```

## Development Setup

### Prerequisites

- Python 3.14 or higher
- uv package manager
- Docker and Docker Compose
- Redis 7+ (for local development)
- Make (optional)

### Initial Setup

1. **Install uv** (if not already installed):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:

   ```bash
   uv sync --all-extras --dev
   ```

3. **Set up environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Start development environment**:

   ```bash
   docker-compose up -d redis
   ```

5. **Run the service**:

   ```bash
   uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Development Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Run tests frequently**:

   ```bash
   uv run pytest
   ```

4. **Commit your changes** following commit guidelines

5. **Keep your branch updated**:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

6. **Push to your fork**:

   ```bash
   git push origin feature/your-feature-name
   ```

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Specific test file
uv run pytest tests/test_specific.py

# Verbose output
uv run pytest -v
```

### Writing Tests

- Write unit tests for all new functionality
- Integration tests for API endpoints and Redis interactions
- Use pytest fixtures for test setup
- Aim for >80% code coverage
- Test edge cases and error conditions

### Test Guidelines

- Use descriptive test names: `test_function_name_scenario_expected_behavior`
- Use pytest fixtures for common setup
- Mock external dependencies
- Clean up resources in test teardown

## Code Style

### Python Code Standards

```bash
# Format code
uv run ruff format .

# Run linter
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Run type checker
uv run mypy src

# Run security checks
uv run bandit -r src

# Run all checks with pre-commit
prek run --all-files
```

### Style Guidelines

- Follow PEP 8 and PEP 484 (type hints)
- Use meaningful variable and function names
- Keep functions small and focused
- Document public functions with docstrings
- Add comments for complex logic
- Use type hints for all function signatures

### Package Organization

- `src/app/` - Main application code
- `src/app/api/` - API routes and endpoints
- `src/app/core/` - Core functionality (config, security, etc.)
- `src/app/auth/` - Authentication and authorization
- `src/app/worker/` - Background job processing
- `src/app/observability/` - Metrics and tracing
- `tests/` - Test files

## Commit Guidelines

### Commit Message Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes
- `security`: Security fixes
- `deps`: Dependency updates

### Examples

```text
feat(api): add recipe URL validation endpoint

Implements URL validation before scraping to prevent
invalid URLs from being processed.

Fixes #123
```

```text
fix(cache): prevent race condition in Redis cache

Added proper locking mechanism to prevent concurrent
cache updates from causing data inconsistency.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Run all checks**:

   ```bash
   prek run --all-files
   uv run pytest
   ```

2. **Update documentation** if needed:
   - README.md
   - CLAUDE.md
   - API documentation
   - Code comments

3. **Ensure no secrets** are committed:
   - Check for API keys, tokens, passwords
   - Review `.env` files
   - Use `.gitignore` appropriately

### PR Requirements

- [ ] Clear description of changes
- [ ] Related issue linked
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All CI checks passing
- [ ] No merge conflicts
- [ ] Commits follow convention
- [ ] No sensitive data committed

### PR Template

The project uses a PR template. Fill it out completely:

- Description of changes
- Type of change
- Security implications
- Breaking changes
- Testing performed
- Configuration changes

### Review Process

1. Maintainers will review your PR
2. Address feedback and requested changes
3. Keep PR updated with main branch
4. Once approved, maintainer will merge

### CI/CD Pipeline

PRs must pass:

- Python build (uv sync)
- Unit tests (pytest)
- Linting (ruff)
- Type checking (mypy)
- Security scanning (bandit)
- Code formatting checks (ruff format)

## Security

### Reporting Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Use [GitHub Security Advisories](https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new) to
report security issues privately.

### Security Guidelines

- Never commit secrets or credentials
- Validate all inputs
- Use parameterized queries
- Implement proper rate limiting
- Follow OAuth2/JWT security best practices
- Keep dependencies updated

## Questions?

- Check the [README](../README.md)
- Review existing [issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues)
- Start a [discussion](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions)
- See [SUPPORT.md](SUPPORT.md) for help resources

Thank you for contributing!
