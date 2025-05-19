# recipe-scraper-service

A FastAPI service for scraping and managing recipe data from various sources.
Includes RESTful APIs for ingredients, recipes, health checks, and more.

## Features

- FastAPI backend with modular architecture
- REST API endpoints for recipes, ingredients, and health
- PostgreSQL database integration (planned)
- Dockerized environment for easy development & deployment
- Pytest-based testing suite with unit, component, and performance tests
- CI/CD pipelines using GitHub Actions (build, lint, test)
- Logging and error handling middleware
- Kubernetes deployment manifests included

## Project Structure

    app/
    ├── api/                # API routers organized by version and resource
    ├── core/               # Core configurations, logging, and security
    ├── db/                 # Database connection & session management
    ├── deps/               # Dependency injection helpers
    ├── exceptions/         # Custom exceptions and handlers
    ├── middleware/         # FastAPI middleware implementations
    ├── models/             # Pydantic models for DB & API schemas
    ├── schemas/            # Request/response schemas organized by type
    ├── services/           # Business logic and external service integrations
    └── utils/              # Utility helpers (date, slugify, validators, etc.)

    tests/
    ├── unit/               # Unit tests for isolated components
    ├── component/          # Component tests covering API endpoints
    ├── dependency/         # Dependency injection tests
    └── performance/        # Performance/load testing scripts

    k8s/                     # Kubernetes manifests
    Dockerfile               # Docker image build
    docker-compose.yml       # Local development docker-compose setup
    .github/workflows/       # GitHub Actions CI/CD workflows
    .env.example             # Sample environment variables template
    .poetry.lock             # Poetry dependency lockfile
    pyproject.toml           # Poetry project metadata and dependencies
    .pre-commit-config.yaml  # Git hooks configuration for linting & formatting
    README.md                # This documentation file

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry
- Docker & Docker Compose (optional but recommended)
- Git

### Setup

1. Clone the repository:

        git clone https://github.com/yourusername/recipe-scraper-service.git
        cd recipe-scraper-service

2. Copy the example environment file and customize as needed:

        cp .env.example .env

3. Install dependencies using Poetry:

        poetry install

4. Activate the virtual environment:

        poetry shell

5. Run the application locally:

        uvicorn app.main:app --reload

    The API will be accessible at `http://localhost:8000`

### Using Docker

Build and run the Docker container:

        docker-compose up --build

    The API will be accessible at `http://localhost:8000`

## Testing

Run all tests with coverage:

        pytest --cov=app tests/

Tests are organized by type in the `tests/` folder.

## CI/CD

The project uses GitHub Actions to automatically:

- Build the Docker image
- Run linting (Black, Ruff)
- Run all tests

Workflows are defined in `.github/workflows/`

## Contributing

Contributions are welcome! Please follow the coding standards and run tests before submitting PRs.

## License

[MIT License](LICENSE)
