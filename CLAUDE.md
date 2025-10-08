# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- **Start locally with reload**: `poetry run dev` or `uvicorn app.main:app --reload`
- **Using Docker**: `docker-compose up --build`
- **Default local URL**: http://localhost:8000

### Testing
- **Run all tests with coverage**: `pytest --cov=app tests/`
- **Run unit tests only**: `poetry run test-unit` or `pytest tests/unit/`
- **Coverage report locations**: `htmlcov/` (HTML), terminal output

### Code Quality
- **Format code**: `black .`
- **Sort imports**: `isort .`
- **Lint code**: `ruff check .` (with auto-fix: `ruff check . --fix`)
- **Type checking**: `mypy app/`
- **Documentation lint**: `pydoclint app/`
- **Security scanning**: `bandit app/` (excluding tests)
- **Dependency vulnerability check**: `safety check`
- **Code complexity**: `radon cc --min B app/` and `radon mi --min B app/`
- **Pre-commit hooks**: `pre-commit run --all-files`

### Dependencies
- **Install dependencies**: `poetry install`
- **Add new dependency**: `poetry add <package>`
- **Update dependencies**: `poetry update`

### Release Management
- **IMPORTANT**: This project uses automated changelog generation from conventional commits
- **Commit format**: Must follow conventional commits (enforced by pre-commit hooks)
- **Version bumps**: Automatic based on commit types (feat = minor, fix = patch, etc.)
- **Manual release**: `gh workflow run release.yml` or push to main branch
- **Setup commit template**: `git config commit.template .gitmessage`

## Architecture Overview

This is a FastAPI-based recipe scraping microservice with a modular, layered architecture:

### Core Structure
- **`app/main.py`**: Application entry point with FastAPI app setup, middleware, and router registration
- **`app/api/v1/`**: Versioned API layer with routes organized by resource (recipes, health, admin, nutritional_info, recommendations)
- **`app/services/`**: Business logic layer including recipe scraping, nutritional analysis, and downstream service integrations (Spoonacular API)
- **`app/db/`**: Database layer with SQLAlchemy models organized by domain (recipes, users, ingredients, meal_plans, nutritional_info)
- **`app/core/`**: Core application components (config, logging, security)

### Key Patterns
- **Schema Organization**: Pydantic schemas in `app/api/v1/schemas/` organized by type:
  - `common/`: Shared schemas (Recipe, Ingredient, pagination, nutritional info components)
  - `request/`: API request schemas
  - `response/`: API response schemas
  - `downstream/`: External API schemas (Spoonacular)
- **Service Dependencies**: Services use dependency injection pattern with mocked services in tests
- **Configuration**: Centralized config in `app/core/config/config.py` with environment variable loading and file-based configs
- **Database Models**: SQLAlchemy models follow domain-driven design with relationship mappings

### External Integrations
- **Recipe Scrapers**: Uses `recipe-scrapers` library for extracting recipe data from web URLs
- **Spoonacular API**: Provides ingredient substitutions, nutritional data, and recipe recommendations
- **Web Scraping**: Custom web scraper in `app/utils/popular_recipe_web_scraper.py` for discovering popular recipes

### Testing Strategy
- **Unit Tests**: Located in `tests/unit/` with comprehensive fixtures in `conftest.py`
- **Integration Tests**: Located in `tests/integration/` using testcontainers for realistic testing
- **Performance Tests**: Located in `tests/performance/` with pytest-benchmark for load testing
- **Test Organization**: Mirror app structure (api/routes, services, db/models, etc.)
- **Mocked Services**: All external dependencies are mocked using pytest fixtures
- **Test Naming Convention**: Files use `*_test.py` pattern (not `test_*.py`)
- **Coverage Target**: 80% minimum coverage requirement (fails build if under)

## Configuration Notes

### Environment Setup
- **Python Version**: 3.13 (strict requirement for compatibility)
- **Poetry**: Used for dependency management and virtual environments
- **Pre-commit hooks**: Comprehensive code quality pipeline with security scanning and conventional commit validation
- Requires `.env` file for database credentials and API keys (see README.md)
- Configuration files in `config/`:
  - `logging.json`: Logging configuration with multiple sinks
  - `recipe_scraping/recipe_blog_urls.json`: Popular recipe website URLs
  - `recipe_scraping/web_scraper.yaml`: Web scraper filtering rules

### Database
- PostgreSQL database with SQLAlchemy ORM
- Database session management in `app/db/session.py`
- Models use base class with common fields (id, created_at, updated_at)

### API Design
- RESTful endpoints with consistent response formats
- Pagination support using limit/offset pattern
- Request/response validation with Pydantic
- OpenAPI documentation generation available at `/docs` and `/redoc`
- Rate limiting and security middleware included
- Comprehensive health checks (`/api/v1/health`, `/api/v1/liveness`, `/api/v1/readiness`)

## Important Implementation Details

- **Error Handling**: Custom exceptions in `app/exceptions/` with global exception handlers
- **Middleware**: Request ID middleware for tracing, logging middleware for request/response logging
- **Caching**: Cache manager utility for performance optimization
- **Unit Conversion**: Built-in unit converter for recipe ingredient quantities
- **Slug Generation**: URL-friendly slug generation for recipes
- **Validation**: Comprehensive validation utilities for recipe data
- **Code Style**: Black formatting (88 char line length), isort for imports, strict MyPy typing
- **Security**: Bandit security scanning, secret detection, dependency vulnerability checks

## Quality Assurance

### Automated Quality Checks
- **Pre-commit pipeline**: Runs formatting, linting, type checking, security scanning, and conventional commit validation
- **Code complexity**: Radon complexity analysis (min grade B required)
- **Documentation**: Google-style doc-strings with pydoclint validation
- **Security**: Multiple security scanners (bandit, safety, detect-secrets)
- **CI/CD Pipeline**: GitHub Actions with automated testing, security scanning, and releases

### Documentation
The project includes comprehensive documentation:
- **README.md**: Main project documentation with features and setup
- **API.md**: Complete API reference with examples and client code
- **.github/CONTRIBUTING.md**: Development workflow and coding standards
- **DEPLOYMENT.md**: Production deployment strategies and configurations
- **.github/SECURITY.md**: Security policies and vulnerability reporting
- **CHANGELOG.md**: Automatically generated from conventional commits

## Conventional Commits

**CRITICAL**: This project strictly enforces conventional commits for automated changelog generation and semantic versioning. Commit messages are validated by pre-commit hooks.

### Required Format
```
<type>[optional scope]: <description>
```

### Important Types
- `feat`: New feature (minor version bump)
- `fix`: Bug fix (patch version bump)
- `security`: Security improvement (patch version bump)
- `docs`: Documentation changes (no version bump)
- `chore`: Maintenance tasks (no version bump)

### Examples
```bash
feat(api): add ingredient substitution endpoint
fix(cache): resolve Redis connection timeout
security(auth): implement rate limiting
docs: update API documentation
```

When working with this codebase, ensure compatibility with the existing patterns, use conventional commits, and utilize the comprehensive test fixtures for consistent testing.
