# Recipe Scraper Service

Enterprise-grade FastAPI microservice for recipe scraping with JWT authentication,
Redis caching, background job processing, and full observability.

## Architecture Overview

```mermaid
flowchart TB
    subgraph External["External Traffic"]
        Client[Client Applications]
        LB[Load Balancer / Ingress]
    end

    subgraph K8s["Kubernetes Cluster"]
        subgraph API["API Layer"]
            direction TB
            API1[API Pod 1]
            API2[API Pod 2]
            HPA[Horizontal Pod Autoscaler]
        end

        subgraph Workers["Background Workers"]
            Worker1[ARQ Worker Pod]
        end

        subgraph Observability["Observability Stack"]
            Prometheus[Prometheus]
            OTLP[OTLP Collector]
        end

        subgraph Storage["Data Layer"]
            Redis[(Redis)]
            subgraph RedisDbs["Redis Databases"]
                Cache[DB 0: Cache]
                Queue[DB 1: Job Queue]
                RateLimit[DB 2: Rate Limits]
            end
        end
    end

    Client --> LB
    LB --> API1 & API2
    HPA -.-> API1 & API2

    API1 & API2 --> Redis
    API1 & API2 --> Queue
    API1 & API2 -.->|metrics| Prometheus
    API1 & API2 -.->|traces| OTLP

    Worker1 --> Queue
    Worker1 --> Cache
    Worker1 -.->|metrics| Prometheus

    Redis --> Cache & Queue & RateLimit
```

### Application Architecture

```mermaid
flowchart TB
    subgraph Request["Incoming Request"]
        HTTP[HTTP Request]
    end

    subgraph Middleware["Middleware Stack"]
        direction TB
        RequestID[Request ID Middleware]
        Timing[Timing Middleware]
        Logging[Logging Middleware]
        Security[Security Headers]
        CORS[CORS Middleware]
    end

    subgraph Auth["Authentication Layer"]
        AuthProvider[Auth Provider]
        JWT[JWT / Introspection]
        Permissions[Permission Checker]
        Dependencies[Auth Dependencies]
    end

    subgraph API["API Layer"]
        Router[API Router v1]
        subgraph Endpoints["Endpoints"]
            Health[Health Routes]
            Future[Future Routes...]
        end
    end

    subgraph Core["Core Services"]
        Exceptions[Exception Handlers]
        Schemas[Pydantic Schemas]
    end

    subgraph Services["Business Logic"]
        ServiceLayer[Service Layer]
        Downstreams[Downstream Clients]
    end

    subgraph Cache["Caching Layer"]
        RateLimiter[Rate Limiter]
        CacheDecorator["@cached Decorator"]
        RedisClient[Redis Client Pool]
    end

    subgraph Workers["Background Processing"]
        JobQueue[Job Enqueue API]
        ARQ[ARQ Worker]
        Tasks[Task Definitions]
    end

    subgraph Observability["Observability"]
        Metrics[Prometheus Metrics]
        Tracing[OpenTelemetry Traces]
        StructuredLogs[Structured Logging]
    end

    subgraph Response["Outgoing Response"]
        HTTPRes[HTTP Response]
    end

    %% Request Flow
    HTTP --> RequestID --> Timing --> Logging --> Security --> CORS
    CORS --> RateLimiter
    RateLimiter --> Router

    Router --> Health
    Router --> Future

    Future --> AuthProvider --> JWT --> Permissions --> Dependencies

    Dependencies --> ServiceLayer
    ServiceLayer --> CacheDecorator --> RedisClient
    ServiceLayer --> Downstreams
    ServiceLayer --> JobQueue --> ARQ --> Tasks

    %% Observability connections
    Timing -.-> Metrics
    Logging -.-> StructuredLogs
    ServiceLayer -.-> Tracing
    RedisClient -.-> Metrics

    %% Response flow
    ServiceLayer --> Schemas --> HTTPRes
    Exceptions -.-> HTTPRes
```

### Request Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant M as Middleware
    participant RL as Rate Limiter
    participant R as Router
    participant A as Auth
    participant S as Service
    participant Ca as Cache
    participant Re as Redis
    participant W as Worker
    participant O as Observability

    C->>M: HTTP Request
    M->>M: Add Request ID
    M->>M: Start Timer
    M->>O: Log Request

    M->>RL: Check Rate Limit
    RL->>Re: Get/Increment Counter
    Re-->>RL: Count

    alt Rate Limited
        RL-->>C: 429 Too Many Requests
    else Allowed
        RL->>R: Forward Request
    end

    R->>A: Authenticate (if protected)
    A->>A: Extract Bearer Token
    A->>A: Decode & Validate JWT
    A->>A: Check Permissions
    A-->>R: User Context

    R->>S: Call Service Method
    S->>Ca: Check Cache
    Ca->>Re: GET cached_key

    alt Cache Hit
        Re-->>Ca: Cached Data
        Ca-->>S: Return Cached
    else Cache Miss
        S->>S: Execute Business Logic
        S->>Ca: Store in Cache
        Ca->>Re: SET cached_key
    end

    opt Async Work Needed
        S->>W: Enqueue Background Job
        W->>Re: LPUSH job_queue
    end

    S-->>R: Response Data
    R-->>M: HTTP Response
    M->>O: Log Response + Timing
    M->>O: Record Metrics
    M-->>C: HTTP Response
```

## Features

- **FastAPI Framework** - Modern async Python web framework with automatic OpenAPI docs
- **JWT Authentication** - Secure token-based auth with access/refresh token flow
- **Redis Caching** - High-performance caching with configurable TTLs
- **Rate Limiting** - Protect endpoints from abuse with SlowAPI
- **Background Jobs** - Async task processing with ARQ (Redis-backed)
- **Full Observability** - Prometheus metrics, OpenTelemetry tracing, structured JSON logging
- **Production Ready** - Multi-stage Docker builds, Kubernetes manifests, HPA, PDB, NetworkPolicies
- **Comprehensive Tests** - 530+ tests with 90%+ coverage (unit, integration, e2e, performance)

## Quick Start

### Prerequisites

- Python 3.14+
- Redis 7+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Local Development

```bash
# Clone and navigate
cd recipe-scraper-service

# Install dependencies with uv
uv sync

# Or with pip
pip install -e ".[dev]"

# Start Redis (Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run the service
uvicorn app.main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Docker

```bash
# Build production image
docker build -t recipe-scraper-service .

# Build development image
docker build --target development -t recipe-scraper-service:dev .

# Run with Docker Compose
docker compose up -d
```

## Project Structure

```text
recipe-scraper-service/
├── src/app/                    # Application source code
│   ├── api/                    # API endpoints
│   │   └── v1/
│   │       ├── endpoints/      # Route handlers
│   │       └── router.py       # API router
│   ├── auth/                   # Authentication
│   │   ├── jwt.py              # JWT token handling
│   │   ├── oauth2.py           # OAuth2 schemes
│   │   ├── permissions.py      # RBAC permissions
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── cache/                  # Caching layer
│   │   ├── redis.py            # Redis client management
│   │   ├── decorators.py       # @cached decorator
│   │   └── rate_limit.py       # Rate limiting
│   ├── core/                   # Core framework
│   │   ├── config.py           # Settings management
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── events/             # Lifecycle events
│   │   └── middleware/         # HTTP middleware
│   ├── observability/          # Monitoring
│   │   ├── logging.py          # Structured logging
│   │   ├── metrics.py          # Prometheus metrics
│   │   └── tracing.py          # OpenTelemetry tracing
│   ├── workers/                # Background jobs
│   │   ├── arq.py              # ARQ configuration
│   │   ├── jobs.py             # Job enqueueing
│   │   └── tasks/              # Task definitions
│   ├── schemas/                # Pydantic models
│   ├── services/               # Business logic
│   └── main.py                 # Application entry
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── e2e/                    # End-to-end tests
│   └── performance/            # Benchmark tests
├── k8s/                        # Kubernetes manifests
│   ├── base/                   # Base resources
│   └── overlays/               # Environment overrides
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
└── pyproject.toml              # Project configuration
```

## API Endpoints

| Endpoint         | Method | Description        | Auth |
| ---------------- | ------ | ------------------ | ---- |
| `/`              | GET    | Service info       | No   |
| `/api/v1/health` | GET    | Liveness probe     | No   |
| `/api/v1/ready`  | GET    | Readiness probe    | No   |
| `/metrics`       | GET    | Prometheus metrics | No   |
| `/docs`          | GET    | OpenAPI Swagger UI | No   |
| `/redoc`         | GET    | OpenAPI ReDoc      | No   |

> **Note**: Authentication is handled by an external auth-service. This service validates
> tokens via configurable providers (introspection, local JWT, or header-based for
> development).

## Configuration

All configuration is via environment variables:

| Variable                          | Default                | Description                                  |
| --------------------------------- | ---------------------- | -------------------------------------------- |
| `APP_NAME`                        | Recipe Scraper Service | Application name                             |
| `ENVIRONMENT`                     | development            | Environment (development/staging/production) |
| `DEBUG`                           | false                  | Enable debug mode                            |
| `JWT_SECRET_KEY`                  | -                      | **Required in production**                   |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30                     | Access token TTL                             |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS`   | 7                      | Refresh token TTL                            |
| `REDIS_HOST`                      | localhost              | Redis hostname                               |
| `REDIS_PORT`                      | 6379                   | Redis port                                   |
| `REDIS_PASSWORD`                  | -                      | Redis password                               |
| `RATE_LIMIT_DEFAULT`              | 100/minute             | Default rate limit                           |
| `RATE_LIMIT_AUTH`                 | 5/minute               | Auth endpoint rate limit                     |
| `OTLP_ENDPOINT`                   | -                      | OpenTelemetry collector endpoint             |
| `LOG_LEVEL`                       | INFO                   | Logging level                                |
| `LOG_FORMAT`                      | json                   | Log format (json/text)                       |

See [docs/configuration.md](docs/configuration.md) for the complete list.

## Documentation

- [Architecture](docs/architecture.md) - System design and component overview
- [API Reference](docs/api.md) - Detailed API documentation
- [Development Guide](docs/development.md) - Local setup and contribution guidelines
- [Deployment Guide](docs/deployment.md) - Production deployment instructions
- [Configuration](docs/configuration.md) - Complete configuration reference

## Testing

```bash
# Run all tests
pytest

# Run by category
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests (requires Redis)
pytest -m e2e           # End-to-end tests
pytest -m performance   # Benchmark tests

# With coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Deployment

### Kubernetes

```bash
# Deploy to development
kubectl apply -k k8s/overlays/development

# Deploy to staging
kubectl apply -k k8s/overlays/staging

# Deploy to production
kubectl apply -k k8s/overlays/production
```

See [docs/deployment.md](docs/deployment.md) for detailed instructions.

## License

MIT License - see [LICENSE](LICENSE) for details.
