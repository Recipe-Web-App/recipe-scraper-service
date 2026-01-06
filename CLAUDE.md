# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## Development Commands

### Running the Application

- **Start locally with reload**: `poetry run dev` or `uvicorn app.main:app --reload`
- **Using Docker**: `docker-compose up --build`
- **Default local URL**: <http://localhost:8000>

### Testing

- **Run all tests with coverage**: `pytest --cov=app tests/`
- **Run unit tests only**: `poetry run test-unit` or `pytest tests/unit/`
- **Run a single test file**: `pytest tests/unit/services/recipe_scraper_service_test.py`
- **Run a single test**: `pytest tests/unit/services/recipe_scraper_service_test.py::test_function_name -v`
- **Coverage report locations**: `htmlcov/` (HTML), terminal output
- **Coverage target**: 80% minimum (fails build if under)

### Code Quality

- **Format code**: `black .`
- **Sort imports**: `isort .`
- **Lint code**: `ruff check .` (with auto-fix: `ruff check . --fix`)
- **Type checking**: `mypy app/`
- **Documentation lint**: `pydoclint app/`
- **Security scanning**: `bandit app/`
- **Dependency vulnerability check**: `safety check`
- **Code complexity**: `radon cc --min B app/` and `radon mi --min B app/`
- **Pre-commit hooks**: `pre-commit run --all-files`

### Dependencies

- **Install dependencies**: `poetry install`
- **Add new dependency**: `poetry add <package>`
- **Update dependencies**: `poetry update`

### Release Management

- **IMPORTANT**: Uses automated changelog generation from conventional commits
- **Commit format**: Must follow conventional commits (enforced by pre-commit hooks)
- **Version bumps**: Automatic based on commit types (feat = minor, fix = patch)
- **Manual release**: `gh workflow run release.yml` or push to main branch
- **Setup commit template**: `git config commit.template .gitmessage`

## Architecture Overview

This is a FastAPI-based recipe scraping microservice with a modular, layered architecture.

### Core Structure

- **`app/main.py`**: Application entry point with FastAPI app, middleware, and router registration
- **`app/api/v1/routes/`**: Versioned API endpoints (recipes, health, admin, nutritional_info, recommendations, shopping)
- **`app/services/`**: Business logic layer including recipe scraping and downstream service integrations
- **`app/services/downstream/`**: External API integrations (Spoonacular, Kroger, notification, user management)
- **`app/db/models/`**: SQLAlchemy models organized by domain (recipes, users, ingredients, meal_plans, nutritional_info)
- **`app/deps/`**: Dependency injection (auth, database sessions, service managers)
- **`app/core/`**: Core application components (config, logging, security)

### Schema Organization

Pydantic schemas in `app/api/v1/schemas/` organized by type:

- `common/`: Shared schemas (Recipe, Ingredient, pagination, nutritional info)
- `request/`: API request schemas
- `response/`: API response schemas
- `downstream/`: External API schemas (Spoonacular, Kroger, Auth Service, User Management)

### Authentication Patterns

Three authentication dependency aliases in `app/deps/auth.py`:

```python
from app.deps.auth import OptionalAuth, RequiredAuth, ServiceToServiceAuth

# Public endpoints - token optional
@router.get("/recipes")
async def get_recipes(user: OptionalAuth): ...

# Protected endpoints - token required
@router.get("/recipes/favorites")
async def get_favorites(user: RequiredAuth): ...

# Admin/internal endpoints - service-to-service only
@router.post("/admin/sync")
async def sync(user: ServiceToServiceAuth): ...
```

### Downstream Service Pattern

External services in `app/services/downstream/` inherit from `BaseService`:

- `SpoonacularService`: Nutritional data, substitutions, recipe recommendations
- `KrogerService`: Product pricing and store inventory
- `NotificationService`: Email and push notifications
- `UserManagementService`: User profiles and preferences

Services are accessed via `DownstreamServiceManager` in `app/deps/downstream_service_manager.py`.

### Caching Architecture

Multi-tier cache in `app/utils/cache_manager.py` (EnhancedCacheManager):

1. **L1 (Memory)**: In-process dictionary, fastest
2. **L2 (Redis)**: Persistent, shared across instances
3. **L3 (File)**: Fallback when Redis unavailable

### Testing Strategy

- **Unit Tests**: `tests/unit/` with mocked dependencies (fixtures in `conftest.py`)
- **Component Tests**: `tests/component/` for integration testing
- **Performance Tests**: `tests/performance/` with pytest-benchmark
- **Test Naming**: Files use `*_test.py` pattern (not `test_*.py`)
- **Mocked Services**: All external dependencies mocked via pytest fixtures

### Key Environment Variables

```bash
# Database
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_SCHEMA
RECIPE_SCRAPER_DB_USER, RECIPE_SCRAPER_DB_PASSWORD

# External APIs
SPOONACULAR_API_KEY
KROGER_API_CLIENT_ID, KROGER_API_CLIENT_SECRET

# Caching
REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

# Security
JWT_SECRET  # min 32 chars
OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET
OAUTH2_SERVICE_ENABLED, OAUTH2_INTROSPECTION_ENABLED
```

### Configuration Files

- `config/logging.json`: Logging configuration
- `config/recipe_scraping/recipe_blog_urls.json`: Popular recipe website URLs
- `config/recipe_scraping/web_scraper.yaml`: Web scraper filtering rules
- `config/service_urls.yaml`: Downstream service endpoints

## Implementation Details

- **Error Handling**: Custom exceptions in `app/exceptions/` with global handlers
- **Middleware**: Request ID (tracing), security headers, process time, logging
- **Database**: PostgreSQL with SQLAlchemy, models use `recipe_manager` schema
- **API Design**: RESTful with pagination (limit/offset), health checks at `/api/v1/health`, `/api/v1/liveness`, `/api/v1/readiness`
- **Code Style**: Black (88 chars), isort, strict MyPy typing, Google-style docstrings

## Conventional Commits

**CRITICAL**: This project strictly enforces conventional commits for automated changelog generation.

```bash
<type>[optional scope]: <description>
```

### Types

- `feat`: New feature (minor version bump)
- `fix`: Bug fix (patch version bump)
- `security`: Security improvement (patch version bump)
- `docs`: Documentation (no version bump)
- `refactor`, `test`, `chore`: No version bump

### Scopes

`api`, `scraper`, `nutritional`, `cache`, `db`, `auth`, `deps`

### Examples

```bash
feat(api): add ingredient substitution endpoint
fix(scraper): handle missing recipe images gracefully
security(auth): implement rate limiting
```
