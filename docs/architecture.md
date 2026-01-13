# Architecture

This document provides a deep dive into the Recipe Scraper Service architecture,
covering design decisions, component interactions, and implementation patterns.

## System Overview

The service follows a layered architecture pattern with clear separation of concerns:

```mermaid
flowchart TB
    subgraph Presentation["Presentation Layer"]
        API[FastAPI Routes]
        Schemas[Pydantic Schemas]
        Middleware[Middleware Stack]
    end

    subgraph Application["Application Layer"]
        Services[Service Classes]
        Auth[Authentication]
        Jobs[Job Enqueueing]
    end

    subgraph Domain["Domain Layer"]
        Models[Domain Models]
        Rules[Business Rules]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        Cache[Redis Cache]
        Queue[Redis Queue]
        Clients[HTTP Clients]
        LLM[LLM Client]
        Telemetry[Observability]
    end

    Presentation --> Application
    Application --> Domain
    Application --> Infrastructure
```

## Component Deep Dive

### Middleware Stack

Requests pass through multiple middleware layers before reaching route handlers:

```mermaid
flowchart LR
    subgraph Middleware["Middleware Pipeline"]
        direction LR
        A[Request ID] --> B[Timing]
        B --> C[Logging]
        C --> D[Security Headers]
        D --> E[CORS]
        E --> F[Rate Limiting]
    end

    Request([Request]) --> A
    F --> Handler([Route Handler])
    Handler --> Response([Response])
```

| Middleware       | Purpose                                                | Location                              |
| ---------------- | ------------------------------------------------------ | ------------------------------------- |
| Request ID       | Adds unique `X-Request-ID` header for tracing          | `core/middleware/request_id.py`       |
| Timing           | Records request duration, adds `X-Process-Time` header | `core/middleware/timing.py`           |
| Logging          | Logs request/response with structured JSON             | `core/middleware/logging.py`          |
| Security Headers | Adds security headers (CSP, X-Frame-Options, etc.)     | `core/middleware/security_headers.py` |
| CORS             | Cross-Origin Resource Sharing handling                 | FastAPI built-in                      |
| Rate Limiting    | Request throttling via SlowAPI + Redis                 | `cache/rate_limit.py`                 |

### Authentication Flow

The service uses a pluggable authentication provider pattern that supports multiple modes:

```mermaid
flowchart TB
    subgraph Modes["Authentication Modes"]
        Introspection["Introspection Mode\n(Production)"]
        LocalJWT["Local JWT Mode\n(Distributed)"]
        Header["Header Mode\n(Development)"]
    end

    subgraph Providers["Auth Providers"]
        IntrospectionProvider[IntrospectionAuthProvider]
        LocalProvider[LocalJWTAuthProvider]
        HeaderProvider[HeaderAuthProvider]
    end

    Introspection --> IntrospectionProvider
    LocalJWT --> LocalProvider
    Header --> HeaderProvider

    IntrospectionProvider -->|HTTP POST| AuthService[(External Auth Service)]
    LocalProvider -->|Decode| JWT[JWT Library]
    HeaderProvider -->|Read| Headers[Request Headers]
```

#### Mode Selection

| Mode            | Use Case                                | Configuration                               |
| --------------- | --------------------------------------- | ------------------------------------------- |
| `introspection` | Production with centralized auth        | `AUTH_SERVICE_URL`, client credentials      |
| `local_jwt`     | Distributed systems, offline validation | `JWT_SECRET_KEY` (shared with auth-service) |
| `header`        | Local development, testing              | Header names (`X-User-ID`, etc.)            |
| `disabled`      | Internal services, testing              | None                                        |

#### Introspection Mode Flow

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant API as Recipe API
    participant Cache as Redis Cache
    participant Auth as Auth Service

    C->>API: GET /api/v1/recipe-scraper/recipes + Bearer token
    API->>Cache: Check token cache

    alt Token Cached
        Cache-->>API: Cached AuthResult
    else Not Cached
        API->>Auth: POST /oauth2/introspect
        Auth-->>API: {active: true, sub, scope, ...}
        API->>Cache: Cache result (TTL: 60s)
    end

    API->>API: Check permissions
    API-->>C: Recipe data
```

#### AuthResult Model

```mermaid
classDiagram
    class AuthResult {
        +user_id: str
        +roles: list~str~
        +permissions: list~str~
        +scopes: list~str~
        +token_type: str
        +issuer: str | None
        +audience: list~str~
        +expires_at: int | None
        +issued_at: int | None
        +raw_claims: dict
    }

    class AuthProvider {
        <<protocol>>
        +provider_name: str
        +validate_token(token, request): AuthResult
        +initialize(): None
        +shutdown(): None
    }

    AuthProvider ..> AuthResult : returns
```

#### Provider Factory

The factory creates the appropriate provider based on `AUTH_MODE`:

```python
# Configuration determines which provider is used
AUTH_MODE=introspection  # Uses IntrospectionAuthProvider
AUTH_MODE=local_jwt      # Uses LocalJWTAuthProvider
AUTH_MODE=header         # Uses HeaderAuthProvider
AUTH_MODE=disabled       # Uses DisabledAuthProvider
```

### Permission System

Role-Based Access Control (RBAC) with hierarchical permissions:

```mermaid
flowchart TB
    subgraph Roles["Roles"]
        Admin[admin]
        User[user]
        Service[service]
    end

    subgraph Permissions["Permissions"]
        Read[read]
        Write[write]
        Delete[delete]
        AdminPerm[admin]
    end

    Admin --> Read & Write & Delete & AdminPerm
    User --> Read & Write
    Service --> Read & Write & Delete
```

### Caching Layer

Multi-purpose Redis usage with database isolation:

```mermaid
flowchart TB
    subgraph Redis["Redis Server"]
        subgraph DB0["Database 0: Cache"]
            AppCache[Application Cache]
            ResponseCache[Response Cache]
        end

        subgraph DB1["Database 1: Queue"]
            JobQueue[ARQ Job Queue]
            JobResults[Job Results]
        end

        subgraph DB2["Database 2: Rate Limits"]
            RateLimitCounters[Request Counters]
        end
    end

    API[API Service] --> DB0
    API --> DB1
    API --> DB2
    Worker[ARQ Worker] --> DB1
```

#### Cache Decorator

The `@cached` decorator provides transparent caching:

```mermaid
flowchart TB
    Call["Function Call"] --> Check{"Cache\nExists?"}
    Check -->|Yes| Return["Return Cached"]
    Check -->|No| Execute["Execute Function"]
    Execute --> Store["Store in Cache"]
    Store --> ReturnNew["Return Result"]

    Store -.->|TTL| Expire["Auto-Expire"]
```

### Background Job Processing

Async task processing with ARQ (Async Redis Queue):

```mermaid
flowchart TB
    subgraph API["API Process"]
        Endpoint[API Endpoint]
        Enqueue[enqueue_job]
    end

    subgraph Redis["Redis DB 1"]
        Queue[(Job Queue)]
        Results[(Results Store)]
    end

    subgraph Worker["Worker Process"]
        ARQ[ARQ Worker]
        subgraph Tasks["Task Handlers"]
            Task1[process_recipe_scrape]
            Task2[send_notification]
            Task3[cleanup_expired_cache]
        end
    end

    Endpoint --> Enqueue
    Enqueue -->|LPUSH| Queue
    ARQ -->|BRPOP| Queue
    ARQ --> Task1 & Task2 & Task3
    Task1 & Task2 & Task3 -->|Store| Results
    Results -->|Poll| API
```

#### Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Queued: enqueue_job()
    Queued --> InProgress: Worker picks up
    InProgress --> Complete: Success
    InProgress --> Failed: Error
    Failed --> Queued: Retry (if retries left)
    Failed --> [*]: Max retries exceeded
    Complete --> [*]: Result stored
```

### LLM Integration

AI-powered features using a fallback-enabled LLM client with Redis caching:

```mermaid
flowchart TB
    subgraph Service["Recipe Scraper Service (K8s)"]
        API[API Endpoint]
        Fallback[FallbackLLMClient]
        Primary[OllamaClient]
        Secondary[GroqClient]
        Cache[(Redis Cache)]
    end

    subgraph Host["Desktop Host"]
        Ollama[Ollama Service]
        GPU[RTX 5070 GPU]
    end

    subgraph Cloud["Groq Cloud"]
        GroqAPI[Groq API]
    end

    API --> Fallback
    Fallback --> Primary
    Fallback -.->|"on failure"| Secondary
    Primary --> Cache
    Secondary --> Cache
    Primary -->|"HTTP :11434"| Ollama
    Secondary -->|"HTTPS"| GroqAPI
    Ollama --> GPU
```

#### Provider Strategy

| Provider   | Role     | Description                             |
| ---------- | -------- | --------------------------------------- |
| **Ollama** | Primary  | Local inference on host GPU (RTX 5070)  |
| **Groq**   | Fallback | Cloud inference when Ollama unavailable |

#### Why Host-Based Ollama?

Ollama runs on the desktop host (not in K8s) to:

- **Share GPU with display server** - The desktop GPU serves 4 monitors and LLM inference
- **Simplify deployment** - No GPU scheduling complexity in K8s
- **Resource efficiency** - Single Ollama instance serves all environments

#### LLM Request Flow

```mermaid
sequenceDiagram
    autonumber
    participant API as Recipe API
    participant Fallback as FallbackLLMClient
    participant Cache as Redis Cache
    participant Ollama as Ollama (Primary)
    participant Groq as Groq (Fallback)

    API->>Fallback: generate_structured(prompt, schema)
    Fallback->>Cache: Check cache (hash of prompt+model+schema)

    alt Cache Hit
        Cache-->>Fallback: Cached result
        Fallback-->>API: LLMCompletionResult (cached=True)
    else Cache Miss
        Fallback->>Ollama: POST /api/generate
        alt Ollama Available
            Ollama-->>Fallback: JSON response
        else Ollama Unavailable
            Ollama--xFallback: Connection Error
            Fallback->>Groq: POST /chat/completions
            Groq-->>Fallback: JSON response
        end
        Fallback->>Fallback: Validate against Pydantic schema
        Fallback->>Cache: Store result (TTL: 1hr)
        Fallback-->>API: LLMCompletionResult (cached=False)
    end
```

#### LLM Use Cases

| Feature            | Description                                  | Output Schema      |
| ------------------ | -------------------------------------------- | ------------------ |
| Recipe Extraction  | Parse unstructured HTML into structured data | `ExtractedRecipe`  |
| Ingredient Parsing | Normalize ingredient text (qty, unit, name)  | `ParsedIngredient` |
| Substitutions      | AI-powered ingredient substitution           | `SubstitutionList` |
| Pairings           | Recipe pairing recommendations               | `PairingResult`    |

See [LLM Integration Guide](./llm.md) for client usage and configuration.

### Observability Stack

Three pillars of observability: Metrics, Traces, and Logs:

```mermaid
flowchart TB
    subgraph App["Application"]
        Code[Application Code]
        Instrumentation[Auto-Instrumentation]
    end

    subgraph Metrics["Metrics (Prometheus)"]
        Counter[Counters]
        Histogram[Histograms]
        Gauge[Gauges]
    end

    subgraph Traces["Traces (OpenTelemetry)"]
        Spans[Spans]
        Context[Trace Context]
    end

    subgraph Logs["Logs (Loguru)"]
        Structured[Structured JSON]
        RequestID[Request ID Correlation]
    end

    Code --> Instrumentation
    Instrumentation --> Counter & Histogram & Gauge
    Instrumentation --> Spans & Context
    Instrumentation --> Structured & RequestID

    Counter & Histogram & Gauge --> Prometheus[(Prometheus)]
    Spans & Context --> Collector[OTLP Collector]
    Structured & RequestID --> Stdout[stdout/stderr]
```

#### Metrics Collected

| Metric                          | Type      | Description                                 |
| ------------------------------- | --------- | ------------------------------------------- |
| `http_requests_total`           | Counter   | Total HTTP requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution                |
| `http_requests_in_progress`     | Gauge     | Currently processing requests               |
| `redis_operations_total`        | Counter   | Redis operations by command                 |
| `background_jobs_total`         | Counter   | Jobs enqueued by task type                  |

### Error Handling

Centralized exception handling with consistent error responses:

```mermaid
flowchart TB
    subgraph Exceptions["Exception Hierarchy"]
        Base[AppException]
        Auth[AuthenticationError]
        Authz[AuthorizationError]
        NotFound[NotFoundError]
        Validation[ValidationError]
        RateLimit[RateLimitError]
    end

    subgraph Handlers["Exception Handlers"]
        AppHandler[App Exception Handler]
        HTTPHandler[HTTP Exception Handler]
        DefaultHandler[Default Handler]
    end

    subgraph Response["Error Response"]
        JSON["{\n  error: string,\n  detail: string,\n  request_id: string\n}"]
    end

    Base --> Auth & Authz & NotFound & Validation & RateLimit
    Auth & Authz & NotFound & Validation & RateLimit --> AppHandler
    AppHandler --> JSON
    HTTPHandler --> JSON
    DefaultHandler --> JSON
```

## Data Flow Examples

### Recipe Scrape Request

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant API as API Service
    participant Cache as Redis Cache
    participant Queue as Redis Queue
    participant Worker as ARQ Worker
    participant External as External Site

    C->>API: POST /api/v1/recipe-scraper/recipes {url}
    API->>API: Validate URL
    API->>Cache: Check if recently scraped

    alt Cached
        Cache-->>API: Cached recipe data
        API-->>C: 200 {recipe}
    else Not Cached
        API->>Queue: Enqueue scrape job
        Queue-->>API: Job ID
        API-->>C: 202 {job_id, status: "processing"}

        Worker->>Queue: Pick up job
        Worker->>External: Fetch recipe page
        External-->>Worker: HTML content
        Worker->>Worker: Parse recipe data
        Worker->>Cache: Store parsed recipe
        Worker->>Queue: Mark job complete

        C->>API: GET /jobs/{job_id}
        API->>Queue: Get job status
        Queue-->>API: Complete + result
        API-->>C: 200 {status: "complete", recipe}
    end
```

## Design Decisions

### Why FastAPI?

- **Async-first**: Built on Starlette with native async/await support
- **Type Safety**: Pydantic integration for request/response validation
- **Auto-documentation**: OpenAPI spec generated from type hints
- **Performance**: One of the fastest Python web frameworks

### Why Redis for Everything?

Using Redis for cache, queue, and rate limiting simplifies operations:

- Single dependency to manage
- Database isolation via separate DB numbers
- Atomic operations for rate limiting
- Pub/sub capability for future features

### Why ARQ over Celery?

- **Async Native**: Built for async/await from the ground up
- **Lightweight**: Minimal dependencies, simple API
- **Redis Only**: No broker abstraction overhead
- **Type Hints**: Full typing support

## Security Considerations

```mermaid
flowchart TB
    subgraph Security["Security Layers"]
        HTTPS[HTTPS Only]
        Headers[Security Headers]
        CORS[CORS Policy]
        RateLimit[Rate Limiting]
        Auth[JWT Auth]
        RBAC[Permission Checks]
        Validation[Input Validation]
    end

    Request([Request]) --> HTTPS
    HTTPS --> Headers --> CORS --> RateLimit
    RateLimit --> Auth --> RBAC --> Validation
    Validation --> Handler([Handler])
```

- **Transport**: TLS termination at ingress/load balancer
- **Headers**: CSP, X-Frame-Options, X-Content-Type-Options
- **Authentication**: JWT with short-lived access tokens
- **Authorization**: Role-based with explicit permission checks
- **Rate Limiting**: Per-IP and per-user limits
- **Input Validation**: Pydantic models for all inputs
