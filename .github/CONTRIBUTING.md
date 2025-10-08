# Contributing to Recipe Scraper Service

Thank you for your interest in contributing to the Recipe Scraper Service! This
document provides guidelines and instructions for contributing to this project.

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
- [Questions](#questions)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected
to uphold this standard. Please refer to
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

## Getting Started

### Prerequisites

- **Python 3.13+** (strict requirement for compatibility)
- **Poetry** for dependency management
- **PostgreSQL** for database
- **Redis** (optional, for caching)
- **Git** for version control

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/recipe-scraper-service.git
   cd recipe-scraper-service
   ```

3. Add the upstream repository:

   ```bash
   git remote add upstream https://github.com/Recipe-Web-App/recipe-scraper-service.git
   ```

## Development Setup

### Install Dependencies

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### Environment Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your local configuration:
   - Database credentials
   - API keys (Spoonacular API, etc.)
   - Redis connection string (if using caching)

### Database Setup

```bash
# Ensure PostgreSQL is running
# Create the database (update credentials in .env first)
# Run any necessary migrations
```

### Verify Setup

```bash
# Run tests to verify everything is working
poetry run pytest

# Start the development server
poetry run dev
# Or: uvicorn app.main:app --reload

# Visit http://localhost:8000/docs for API documentation
```

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/your-feature-name` - Feature branches
- `fix/your-bug-fix` - Bug fix branches

### Creating a Feature Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create and switch to a new feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. Make your changes in logical, focused commits
2. Write or update tests for your changes
3. Update documentation as needed
4. Run tests and linters before committing

## Testing

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=app tests/

# Run unit tests only
poetry run test-unit
# Or: pytest tests/unit/

# Run specific test file
pytest tests/unit/test_recipe_service.py

# Run with verbose output
pytest -v
```

### Test Coverage Requirements

- Minimum coverage: **80%**
- Coverage must not decrease with new changes
- All new features must include tests
- Bug fixes should include regression tests

### Test Organization

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Performance tests: `tests/performance/`
- Follow existing test structure and naming conventions

### Writing Tests

```python
# Use descriptive test names
def test_scrape_recipe_returns_valid_recipe_data():
    # Arrange
    url = "https://example.com/recipe"

    # Act
    result = scrape_recipe(url)

    # Assert
    assert result is not None
    assert result.title
    assert result.ingredients
```

## Code Style

This project follows strict code quality standards enforced by pre-commit hooks.

### Formatting

```bash
# Format code with Black (88 character line length)
poetry run black .

# Sort imports with isort
poetry run isort .

# Or run both via pre-commit
pre-commit run --all-files
```

### Linting

```bash
# Run Ruff linter
poetry run ruff check .

# Auto-fix issues where possible
poetry run ruff check . --fix
```

### Type Checking

```bash
# Run MyPy for static type checking
poetry run mypy app/
```

### Documentation Linting

```bash
# Check docstring quality
poetry run pydoclint app/
```

### Security Scanning

```bash
# Run Bandit security scanner
poetry run bandit app/

# Check for known vulnerabilities in dependencies
poetry run safety check
```

### Code Complexity

```bash
# Check cyclomatic complexity
poetry run radon cc --min B app/

# Check maintainability index
poetry run radon mi --min B app/
```

### Pre-commit Hooks

This project uses pre-commit hooks to enforce code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```

Hooks will automatically run on `git commit` and include:

- Black formatting
- isort import sorting
- Ruff linting
- MyPy type checking
- Bandit security scanning
- Conventional commit message validation

## Commit Guidelines

This project strictly enforces **Conventional Commits** for automated
changelog generation and semantic versioning.

### Commit Message Format

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

- `feat`: New feature (minor version bump)
- `fix`: Bug fix (patch version bump)
- `security`: Security improvement (patch version bump)
- `docs`: Documentation changes (no version bump)
- `style`: Code style/formatting (no version bump)
- `refactor`: Code refactoring (no version bump)
- `perf`: Performance improvement (no version bump)
- `test`: Adding or updating tests (no version bump)
- `chore`: Maintenance tasks (no version bump)
- `ci`: CI/CD changes (no version bump)
- `deps`: Dependency updates (no version bump)

### Scope Examples

- `api`: API changes
- `scraper`: Recipe scraping functionality
- `nutritional`: Nutritional analysis
- `cache`: Caching functionality
- `db`: Database changes

### Commit Examples

```bash
# Good commits
feat(api): add ingredient substitution endpoint
fix(scraper): handle missing recipe images gracefully
security(auth): implement rate limiting on auth endpoints
docs: update API documentation with new endpoints
refactor(cache): improve Redis connection handling
test(scraper): add tests for popular recipe websites

# Breaking changes (adds BREAKING CHANGE to footer)
feat(api)!: redesign recipe response schema

BREAKING CHANGE: Recipe response now includes nutritional_info as nested object
```

### Set Up Commit Template

```bash
git config commit.template .gitmessage
```

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all quality checks**:

   ```bash
   # Format code
   poetry run black .
   poetry run isort .

   # Lint code
   poetry run ruff check .

   # Type check
   poetry run mypy app/

   # Run tests
   pytest --cov=app tests/

   # Security scan
   poetry run bandit app/

   # Or run pre-commit hooks
   pre-commit run --all-files
   ```

3. **Ensure tests pass** and coverage meets requirements (80% minimum)

4. **Update documentation** if you've changed APIs or added features

### Creating a Pull Request

1. Push your branch to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

2. Go to the repository on GitHub and click "New Pull Request"

3. Fill out the pull request template completely:
   - Clear description of changes
   - Link to related issues
   - Type of change
   - Testing performed
   - Screenshots/logs if applicable

4. Ensure all automated checks pass:
   - CI pipeline
   - Test coverage
   - Code quality checks
   - Security scans

### Review Process

- A maintainer will review your PR
- Address any feedback or requested changes
- Keep your PR updated with the base branch
- Once approved, a maintainer will merge your PR

### PR Requirements

- [ ] All tests pass
- [ ] Code coverage meets 80% minimum
- [ ] No security vulnerabilities introduced
- [ ] Code follows style guidelines
- [ ] Commit messages follow conventional commits
- [ ] Documentation updated if needed
- [ ] PR template filled out completely

## Security

### Reporting Vulnerabilities

**DO NOT** create public issues for security vulnerabilities.

Instead, please report security issues via:

- **GitHub Security Advisories**: <https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new>

For more information, see [SECURITY.md](SECURITY.md).

### Security Best Practices

- Never commit secrets, API keys, or credentials
- Use environment variables for sensitive configuration
- Run security scans before submitting PRs (`bandit`, `safety check`)
- Follow OWASP guidelines for web security
- Validate and sanitize all user input
- Use parameterized queries to prevent SQL injection

## Questions

If you have questions about contributing:

1. Check the [README.md](../README.md) for general information
2. Review [SUPPORT.md](SUPPORT.md) for help resources
3. Search [existing issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues)
4. Ask in [GitHub Discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions)
5. Check the [API documentation](../API.md)

## Additional Resources

- [README.md](../README.md) - Project overview and setup
- [API.md](../API.md) - API documentation
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment guides
- [SECURITY.md](SECURITY.md) - Security policies
- [CLAUDE.md](../CLAUDE.md) - Development commands and architecture

Thank you for contributing to the Recipe Scraper Service!
