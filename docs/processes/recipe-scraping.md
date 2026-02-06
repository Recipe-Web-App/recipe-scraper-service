# Recipe Scraping Process

This document explains the complete flow of scraping a recipe from the web and storing it in the database. The process
involves multiple services, middleware layers, async job processing, and LLM-powered extraction.

## Table of Contents

1. [Overview](#1-overview)
2. [Request Lifecycle](#2-request-lifecycle)
3. [Middleware Stack](#3-middleware-stack)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Async Job Queue System](#5-async-job-queue-system)
6. [Recipe Processing Pipeline](#6-recipe-processing-pipeline)
7. [LLM Extraction Strategy](#7-llm-extraction-strategy)
8. [Data Models](#8-data-models)
9. [Error Handling](#9-error-handling)
10. [Observability](#10-observability)

---

## 1. Overview

The Recipe Scraper Service is a FastAPI-based microservice that extracts structured recipe data from web pages. It uses
an asynchronous job queue for background processing and LLM-powered extraction for intelligent parsing.

### High-Level Architecture

```mermaid
graph TB
    subgraph Client
        C[Client Application]
    end

    subgraph "Recipe Scraper Service"
        subgraph "FastAPI Application"
            MW[Middleware Stack]
            AUTH[Auth Layer]
            API[API Endpoints]
        end

        subgraph "Background Processing"
            ARQ[ARQ Worker]
            TASKS[Task Functions]
        end

        subgraph "AI/ML"
            LLM_CLIENT[Fallback LLM Client]
            OLLAMA[Ollama - Primary]
            GROQ[Groq - Secondary]
        end
    end

    subgraph "Data Stores"
        REDIS_CACHE[(Redis DB 0<br/>Cache)]
        REDIS_QUEUE[(Redis DB 1<br/>Job Queue)]
        REDIS_RATE[(Redis DB 2<br/>Rate Limiting)]
    end

    subgraph "External"
        WEB[Recipe Websites]
        AUTH_SVC[Auth Service]
    end

    C -->|POST /recipes| MW
    MW --> AUTH
    AUTH -->|Validate Token| AUTH_SVC
    AUTH --> API
    API -->|Enqueue Job| REDIS_QUEUE
    API -->|Check Cache| REDIS_CACHE
    MW -->|Rate Limit| REDIS_RATE

    ARQ -->|Poll Jobs| REDIS_QUEUE
    ARQ --> TASKS
    TASKS -->|Fetch HTML| WEB
    TASKS --> LLM_CLIENT
    LLM_CLIENT --> OLLAMA
    LLM_CLIENT -.->|Fallback| GROQ
    TASKS -->|Store Result| REDIS_CACHE
```

### Key Components

| Component | Purpose                                             |
| --------- | --------------------------------------------------- |
| FastAPI   | Web framework for API endpoints                     |
| ARQ       | Async Redis Queue for background jobs               |
| Redis     | Caching, job queue, and rate limiting (3 databases) |
| Ollama    | Local LLM for recipe extraction                     |
| Groq      | Cloud LLM fallback                                  |
| httpx     | Async HTTP client for web scraping                  |

---

## 2. Request Lifecycle

When a client submits a URL to scrape, the request flows through multiple layers before a job is enqueued.

### Request Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant MW as Middleware Stack
    participant RL as Rate Limiter
    participant AUTH as Auth Layer
    participant API as Endpoint Handler
    participant CACHE as Redis Cache
    participant QUEUE as Redis Queue

    C->>MW: POST /api/v1/recipe-scraper/recipes<br/>{recipe_url: "https://..."}

    Note over MW: Security Headers Added
    MW->>MW: Generate X-Request-ID
    MW->>MW: Start Timing
    MW->>MW: Log Request

    MW->>RL: Check Rate Limit

    alt Rate Limit Exceeded
        RL-->>C: 429 Too Many Requests
    else Rate Limit OK
        RL->>AUTH: Forward Request
    end

    AUTH->>AUTH: Extract Token
    AUTH->>AUTH: Validate Token

    alt Invalid Token
        AUTH-->>C: 401 Unauthorized
    else Valid Token
        AUTH->>AUTH: Check recipe:scrape Permission

        alt No Permission
            AUTH-->>C: 403 Forbidden
        else Has Permission
            AUTH->>API: Forward Request
        end
    end

    API->>API: Validate URL (Pydantic)
    API->>CACHE: Check if Recently Scraped

    alt Cached Recipe Exists
        CACHE-->>API: Return Recipe
        API-->>C: 200 OK {recipe: ...}
    else Not Cached
        API->>QUEUE: Enqueue Job
        QUEUE-->>API: Return Job ID
        API-->>C: 202 Accepted<br/>{job_id: "abc-123", status: "queued"}
    end
```

### Endpoint Details

**Endpoint:** `POST /api/v1/recipe-scraper/recipes`

**Request:**

```json
{
  "recipe_url": "https://example.com/recipe/chocolate-cake"
}
```

**Response (Cached):** `200 OK`

```json
{
  "recipe": {
    "recipe_id": 123,
    "title": "Chocolate Cake",
    "ingredients": [...],
    "steps": [...]
  }
}
```

**Response (Queued):** `202 Accepted`

```json
{
  "job_id": "abc-123-def-456",
  "status": "queued"
}
```

---

## 3. Middleware Stack

The middleware stack processes every request in a specific order. FastAPI executes middleware
in **reverse order of addition** on the request path.

### Middleware Execution Order

```mermaid
flowchart TD
    subgraph "Request Path (Top to Bottom)"
        REQ[Incoming Request]
        SEC[SecurityHeadersMiddleware<br/>Adds X-Content-Type-Options, X-Frame-Options, etc.]
        RID[RequestIDMiddleware<br/>Generates/Propagates X-Request-ID]
        TIM[TimingMiddleware<br/>Starts request timer]
        LOG[LoggingMiddleware<br/>Logs request details as JSON]
        GZIP[GZipMiddleware<br/>Marks response for compression]
        CORS[CORSMiddleware<br/>Handles preflight, adds CORS headers]
        HANDLER[Route Handler]
    end

    subgraph "Response Path (Bottom to Top)"
        RES[Outgoing Response]
    end

    REQ --> SEC --> RID --> TIM --> LOG --> GZIP --> CORS --> HANDLER
    HANDLER --> CORS --> GZIP --> LOG --> TIM --> RID --> SEC --> RES
```

### Middleware Details

| Middleware                  | File                                  | Purpose                                               |
| --------------------------- | ------------------------------------- | ----------------------------------------------------- |
| `SecurityHeadersMiddleware` | `core/middleware/security_headers.py` | Adds security headers (CSP, X-Frame-Options, etc.)    |
| `RequestIDMiddleware`       | `core/middleware/request_id.py`       | Generates unique X-Request-ID for tracing             |
| `TimingMiddleware`          | `core/middleware/timing.py`           | Measures request duration, adds X-Process-Time header |
| `LoggingMiddleware`         | `core/middleware/logging.py`          | Structured JSON logging of requests/responses         |
| `GZipMiddleware`            | FastAPI built-in                      | Compresses responses > 1000 bytes                     |
| `CORSMiddleware`            | FastAPI built-in                      | Handles Cross-Origin Resource Sharing                 |

### Excluded Paths

The logging middleware excludes health/metrics endpoints to reduce noise:

- `/api/v1/recipe-scraper/health`
- `/api/v1/recipe-scraper/ready`
- `/api/v1/recipe-scraper/metrics`

---

## 4. Authentication & Authorization

The service uses a flexible authentication system with multiple modes and role-based access control (RBAC).

### Auth Decision Flow

```mermaid
flowchart TD
    REQ[Request Received] --> CHECK_MODE{Auth Mode?}

    CHECK_MODE -->|disabled| ALLOW[Allow Request]
    CHECK_MODE -->|header| EXTRACT_HEADER[Extract X-User-ID Header]
    CHECK_MODE -->|local_jwt| EXTRACT_JWT[Extract JWT from Authorization]
    CHECK_MODE -->|introspection| EXTRACT_TOKEN[Extract Token]

    EXTRACT_HEADER --> BUILD_USER[Build User Context]

    EXTRACT_JWT --> VALIDATE_JWT{Valid JWT?}
    VALIDATE_JWT -->|No| REJECT_401[401 Unauthorized]
    VALIDATE_JWT -->|Yes| BUILD_USER

    EXTRACT_TOKEN --> CACHE_CHECK{Token in Cache?}
    CACHE_CHECK -->|Yes| BUILD_USER
    CACHE_CHECK -->|No| INTROSPECT[Call Auth Service]
    INTROSPECT --> VALID{Token Valid?}
    VALID -->|No| REJECT_401
    VALID -->|Yes| CACHE_TOKEN[Cache for 60s]
    CACHE_TOKEN --> BUILD_USER

    BUILD_USER --> CHECK_PERM{Has recipe:scrape?}
    CHECK_PERM -->|No| REJECT_403[403 Forbidden]
    CHECK_PERM -->|Yes| ALLOW
```

### Auth Modes

| Mode            | Use Case                      | Token Source                         |
| --------------- | ----------------------------- | ------------------------------------ |
| `disabled`      | Development/Testing           | None required                        |
| `header`        | Development with user context | `X-User-ID` header                   |
| `local_jwt`     | Production with JWT           | `Authorization: Bearer <token>`      |
| `introspection` | Production with external auth | Token validated against auth service |

### Role-Based Access Control

The `recipe:scrape` permission is required to use the scraping endpoint.

```mermaid
flowchart LR
    subgraph "Roles (Hierarchy)"
        USER[USER]
        PREMIUM[PREMIUM]
        MODERATOR[MODERATOR]
        ADMIN[ADMIN]
    end

    subgraph "Permissions"
        READ[recipe:read]
        CREATE[recipe:create]
        SCRAPE[recipe:scrape]
        DELETE[recipe:delete]
        ADMIN_P[admin:*]
    end

    USER --> READ
    USER --> CREATE

    PREMIUM --> READ
    PREMIUM --> CREATE
    PREMIUM --> SCRAPE

    MODERATOR --> READ
    MODERATOR --> CREATE
    MODERATOR --> SCRAPE
    MODERATOR --> DELETE

    ADMIN --> READ
    ADMIN --> CREATE
    ADMIN --> SCRAPE
    ADMIN --> DELETE
    ADMIN --> ADMIN_P
```

| Role      | Can Scrape? | Notes              |
| --------- | ----------- | ------------------ |
| USER      | No          | Basic access only  |
| PREMIUM   | Yes         | Paid feature       |
| MODERATOR | Yes         | Content management |
| ADMIN     | Yes         | Full access        |
| SERVICE   | Yes         | Internal services  |

---

## 5. Async Job Queue System

Recipe scraping is handled asynchronously using ARQ (Async Redis Queue) to avoid blocking API requests.

### Job Processing Flow

```mermaid
sequenceDiagram
    autonumber
    participant API as API Handler
    participant POOL as ARQ Pool
    participant QUEUE as Redis Queue<br/>(DB 1)
    participant WORKER as ARQ Worker
    participant TASK as process_recipe_scrape
    participant RESULT as Job Results

    API->>POOL: get_arq_pool()
    POOL-->>API: ArqRedis connection

    API->>QUEUE: LPUSH job to scraper:queue:jobs
    Note over QUEUE: Job queued with metadata:<br/>function, args, job_id, enqueue_time

    QUEUE-->>API: Job ID
    API-->>API: Return 202 to client

    loop Worker Polling
        WORKER->>QUEUE: BRPOP scraper:queue:jobs
        QUEUE-->>WORKER: Job data
    end

    WORKER->>TASK: Execute process_recipe_scrape(ctx, url, user_id)

    Note over TASK: 1. Fetch URL<br/>2. Parse HTML<br/>3. Extract via LLM<br/>4. Validate schema

    alt Success
        TASK-->>WORKER: {status: "completed", recipe: {...}}
        WORKER->>RESULT: HSET job result (TTL: 1 hour)
    else Failure (attempts < 3)
        TASK--xWORKER: Exception
        WORKER->>QUEUE: Re-queue with job_try + 1
    else Failure (attempts >= 3)
        TASK--xWORKER: Exception
        WORKER->>RESULT: HSET failed result
    end
```

### Worker Configuration

From `src/app/workers/arq.py`:

| Setting            | Value                        | Description                    |
| ------------------ | ---------------------------- | ------------------------------ |
| `queue_name`       | `scraper:queue:jobs`         | Redis key for job queue        |
| `health_check_key` | `scraper:queue:health-check` | Worker health check key        |
| `job_timeout`      | 300s (5 min)                 | Max execution time per job     |
| `max_jobs`         | 10                           | Concurrent jobs per worker     |
| `keep_result`      | 3600s (1 hour)               | How long to keep job results   |
| `max_tries`        | 3                            | Retry attempts for failed jobs |

### Job Status Polling

Clients can poll for job completion:

**Endpoint:** `GET /api/v1/recipe-scraper/jobs/{job_id}`

**Response:**

```json
{
  "job_id": "abc-123-def-456",
  "status": "complete",
  "function": "process_recipe_scrape",
  "enqueue_time": "2024-01-15T10:30:00Z",
  "job_try": 1,
  "result": {
    "status": "completed",
    "url": "https://example.com/recipe",
    "recipe": { ... }
  }
}
```

### Job States

| Status        | Description                            |
| ------------- | -------------------------------------- |
| `queued`      | Job waiting in queue                   |
| `in_progress` | Worker is executing the job            |
| `complete`    | Job finished successfully              |
| `failed`      | Job failed after max retries           |
| `not_found`   | Job ID doesn't exist or result expired |

---

## 6. Recipe Processing Pipeline

Once a job is picked up by a worker, it goes through the processing pipeline.

### Processing Stages

```mermaid
flowchart TD
    START[Job Received] --> FETCH[Fetch URL]

    subgraph "URL Fetching"
        FETCH --> HEADERS[Set Headers<br/>User-Agent, Accept]
        HEADERS --> HTTP[httpx.get&#40;url&#41;]
        HTTP --> CHECK_STATUS{Status 200?}
        CHECK_STATUS -->|No| FETCH_ERR[Raise FetchError]
        CHECK_STATUS -->|Yes| EXTRACT_HTML[Extract HTML Content]
    end

    EXTRACT_HTML --> PARSE[Parse HTML]

    subgraph "HTML Parsing"
        PARSE --> CLEAN[Clean HTML<br/>Remove scripts, styles]
        CLEAN --> IDENTIFY[Identify Recipe Content<br/>JSON-LD, Microdata, hRecipe]
        IDENTIFY --> EXTRACT[Extract Raw Text]
    end

    EXTRACT --> LLM[LLM Extraction]

    subgraph "LLM Processing"
        LLM --> FORMAT[Format Prompt with HTML]
        FORMAT --> GENERATE[generate_structured&#40;&#41;]
        GENERATE --> VALIDATE{Schema Valid?}
        VALIDATE -->|No| LLM_ERR[Raise ValidationError]
        VALIDATE -->|Yes| RECIPE[Structured Recipe]
    end

    RECIPE --> POST[Post-Processing]

    subgraph "Post-Processing"
        POST --> NORMALIZE[Normalize Units]
        NORMALIZE --> DEDUPE[Deduplicate Ingredients]
        DEDUPE --> ENRICH[Enrich Metadata]
    end

    ENRICH --> CACHE_RESULT[Cache Recipe]
    CACHE_RESULT --> DONE[Return Result]

    FETCH_ERR --> FAIL[Job Failed]
    LLM_ERR --> FAIL
```

### URL Fetching

The service uses `httpx` for async HTTP requests with:

- Custom User-Agent to avoid bot detection
- Reasonable timeouts (30s connect, 60s read)
- Redirect following (up to 5 redirects)
- SSL verification

### Structured Data Detection

The parser looks for recipe data in multiple formats:

1. **JSON-LD** (`<script type="application/ld+json">`) - Preferred
2. **Microdata** (`itemtype="https://schema.org/Recipe"`)
3. **hRecipe** microformat (legacy)
4. **Plain text** extraction (fallback for LLM)

---

## 7. LLM Extraction Strategy

The service uses LLMs to intelligently extract structured recipe data from HTML content.

### Prompt Architecture

Prompts are defined using the `BasePrompt` pattern from `src/app/llm/prompts/base.py`:

```python
class BasePrompt[T: BaseModel](ABC):
    """Base class for all LLM prompts."""

    output_schema: ClassVar[type[BaseModel]]  # Pydantic model for output
    system_prompt: ClassVar[str | None] = None
    temperature: ClassVar[float] = 0.1  # Low for deterministic output
    max_tokens: ClassVar[int | None] = None

    @abstractmethod
    def format(self, **kwargs: Any) -> str:
        """Format the prompt template with input variables."""
        ...
```

### Recipe Extraction Prompt Example

```python
class RecipeExtractionPrompt(BasePrompt[Recipe]):
    output_schema = Recipe
    system_prompt = """You are a recipe extraction assistant.
    Extract structured recipe data from the provided HTML content.
    Return ONLY valid JSON matching the schema."""
    temperature = 0.1

    def format(self, html_content: str) -> str:
        return f"""Extract the recipe from this HTML:

{html_content}

Extract: title, description, servings, prep_time, cook_time,
difficulty, ingredients (with quantities), and steps."""
```

### Fallback LLM Architecture

```mermaid
sequenceDiagram
    autonumber
    participant TASK as Task Function
    participant CLIENT as FallbackLLMClient
    participant OLLAMA as Ollama<br/>(localhost:11434)
    participant GROQ as Groq API<br/>(api.groq.com)

    TASK->>CLIENT: generate_structured(prompt, Recipe)

    CLIENT->>OLLAMA: POST /api/generate<br/>{prompt, format: json_schema}

    alt Ollama Available
        OLLAMA-->>CLIENT: {response: "...json..."}
        CLIENT->>CLIENT: Parse & Validate against Recipe schema
        CLIENT-->>TASK: Recipe instance
    else Ollama Unavailable (LLMUnavailableError)
        OLLAMA--xCLIENT: Connection refused / Timeout
        Note over CLIENT: Log warning, attempt fallback

        CLIENT->>GROQ: POST /chat/completions<br/>{messages, response_format: json_object}

        alt Groq Available
            GROQ-->>CLIENT: {choices: [{message: {content: "...json..."}}]}
            CLIENT->>CLIENT: Parse & Validate against Recipe schema
            CLIENT-->>TASK: Recipe instance
        else Groq Also Unavailable
            GROQ--xCLIENT: Error
            CLIENT--xTASK: LLMUnavailableError
        end
    end
```

### Structured Output Generation

The `generate_structured()` method ensures type-safe output:

```python
async def generate_structured(
    self,
    prompt: str,
    schema: type[T],  # e.g., Recipe
    *,
    model: str | None = None,
    system: str | None = None,
    options: dict[str, Any] | None = None,
) -> T:  # Returns validated Recipe instance
```

**Ollama:** Uses the `format` field with a JSON schema derived from the Pydantic model.

**Groq:** Uses OpenAI-compatible `response_format: {"type": "json_object"}` with schema instructions in the prompt.

### LLM Configuration

| Provider | Model                       | Endpoint                                          | Use Case                  |
| -------- | --------------------------- | ------------------------------------------------- | ------------------------- |
| Ollama   | `mistral:7b` (configurable) | `http://localhost:11434/api/generate`             | Primary - Local inference |
| Groq     | `llama-3.1-8b-instant`      | `https://api.groq.com/openai/v1/chat/completions` | Fallback - Cloud API      |

### Fallback Triggers

| Error Type            | Triggers Fallback? | Reason                                 |
| --------------------- | ------------------ | -------------------------------------- |
| `LLMUnavailableError` | Yes                | Connection refused, network error      |
| `LLMTimeoutError`     | Yes                | Request timeout (subclass of above)    |
| `LLMValidationError`  | No                 | Schema mismatch - retrying won't help  |
| `LLMResponseError`    | No                 | HTTP 4xx/5xx errors                    |
| `LLMRateLimitError`   | No                 | Should implement backoff, not fallback |

---

## 8. Data Models

The service uses Pydantic models for request/response validation and LLM output schemas.

### Entity Relationship Diagram

```mermaid
classDiagram
    class CreateRecipeRequest {
        +HttpUrl recipe_url
    }

    class CreateRecipeResponse {
        +Recipe recipe
    }

    class Recipe {
        +int recipe_id
        +str title
        +str description
        +str origin_url
        +float servings
        +int preparation_time
        +int cooking_time
        +Difficulty difficulty
        +list~Ingredient~ ingredients
        +list~RecipeStep~ steps
    }

    class Ingredient {
        +int ingredient_id
        +str name
        +Quantity quantity
    }

    class Quantity {
        +float amount
        +IngredientUnit measurement
    }

    class RecipeStep {
        +int step_number
        +str instruction
        +bool optional
        +int timer_seconds
        +datetime created_at
    }

    class Difficulty {
        <<enumeration>>
        EASY
        MEDIUM
        HARD
    }

    class IngredientUnit {
        <<enumeration>>
        G, KG, OZ, LB
        ML, L, CUP, TBSP, TSP
        PIECE, CLOVE, SLICE, PINCH
        CAN, BOTTLE, PACKET, UNIT
    }

    CreateRecipeRequest ..> Recipe : produces
    CreateRecipeResponse *-- Recipe
    Recipe *-- "1..*" Ingredient
    Recipe *-- "1..*" RecipeStep
    Recipe --> Difficulty
    Ingredient *-- "0..1" Quantity
    Quantity --> IngredientUnit
```

### Schema Definitions

**Location:** `src/app/schemas/`

| File            | Models                                                                |
| --------------- | --------------------------------------------------------------------- |
| `recipe.py`     | `Recipe`, `RecipeStep`, `CreateRecipeRequest`, `CreateRecipeResponse` |
| `ingredient.py` | `Ingredient`, `Quantity`, `WebRecipe`                                 |
| `enums.py`      | `Difficulty`, `IngredientUnit`, `Allergen`, `FoodGroup`               |
| `base.py`       | `APIRequest`, `APIResponse` (base classes)                            |

### IngredientUnit Categories

| Category | Units                                                 |
| -------- | ----------------------------------------------------- |
| Weight   | G, KG, OZ, LB                                         |
| Volume   | ML, L, CUP, TBSP, TSP                                 |
| Count    | PIECE, CLOVE, SLICE, PINCH, CAN, BOTTLE, PACKET, UNIT |

---

## 9. Error Handling

The service uses a structured exception hierarchy with consistent error responses.

### Exception Hierarchy

```mermaid
flowchart TD
    BASE[AppException] --> AUTH_E[AuthenticationError<br/>401]
    BASE --> AUTHZ_E[AuthorizationError<br/>403]
    BASE --> NOT_FOUND[NotFoundError<br/>404]
    BASE --> VALIDATION[ValidationError<br/>422]
    BASE --> RATE_LIMIT[RateLimitError<br/>429]

    subgraph "LLM Exceptions"
        LLM_BASE[LLMError]
        LLM_BASE --> LLM_UNAVAIL[LLMUnavailableError]
        LLM_UNAVAIL --> LLM_TIMEOUT[LLMTimeoutError]
        LLM_BASE --> LLM_VALID[LLMValidationError]
        LLM_BASE --> LLM_RESP[LLMResponseError]
        LLM_BASE --> LLM_RATE[LLMRateLimitError]
    end
```

### HTTP Status Codes

| Code | Meaning               | When Used                          |
| ---- | --------------------- | ---------------------------------- |
| 200  | OK                    | Recipe returned from cache         |
| 202  | Accepted              | Async job enqueued                 |
| 400  | Bad Request           | Invalid URL format                 |
| 401  | Unauthorized          | Missing or invalid token           |
| 403  | Forbidden             | Missing `recipe:scrape` permission |
| 404  | Not Found             | Recipe or job not found            |
| 422  | Unprocessable Entity  | Pydantic validation failed         |
| 429  | Too Many Requests     | Rate limit exceeded                |
| 500  | Internal Server Error | Unhandled exception                |
| 503  | Service Unavailable   | Redis or dependencies down         |

### Error Response Format

```json
{
  "error": "authorization_error",
  "detail": "Missing required permission: recipe:scrape",
  "request_id": "abc-123-def-456"
}
```

### Job Retry Logic

```mermaid
flowchart TD
    JOB[Job Execution] --> SUCCESS{Success?}
    SUCCESS -->|Yes| DONE[Store Result<br/>TTL: 1 hour]
    SUCCESS -->|No| CHECK_TRIES{Attempts < 3?}
    CHECK_TRIES -->|Yes| REQUEUE[Re-queue Job<br/>job_try + 1]
    REQUEUE --> JOB
    CHECK_TRIES -->|No| FAIL[Mark as Failed<br/>Store Error Result]
```

---

## 10. Observability

The service implements comprehensive observability through metrics, tracing, and structured logging.

### Observability Stack

| Component | Tool                                | Purpose                                |
| --------- | ----------------------------------- | -------------------------------------- |
| Metrics   | Prometheus + FastAPI Instrumentator | Request counts, latencies, error rates |
| Tracing   | OpenTelemetry + OTLP                | Distributed request tracing            |
| Logging   | Loguru                              | Structured JSON logging                |

### Prometheus Metrics

**Endpoint:** `GET /api/v1/recipe-scraper/metrics`

Key metrics exposed:

- `http_requests_total` - Request count by method, path, status
- `http_request_duration_seconds` - Request latency histogram
- `redis_operations_total` - Redis command counts
- `arq_jobs_total` - Job counts by status
- `llm_requests_total` - LLM API calls by provider

### Request Tracing

Every request gets a unique `X-Request-ID` that:

1. Is generated by `RequestIDMiddleware` (or accepted from client)
2. Is propagated to all downstream services
3. Is included in all log entries
4. Is returned in the response header
5. Is attached to OpenTelemetry spans

### Structured Logging

All logs are emitted as JSON with consistent fields:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "message": "Enqueued job",
  "request_id": "abc-123-def-456",
  "function": "process_recipe_scrape",
  "job_id": "xyz-789",
  "extra": {
    "url": "https://example.com/recipe"
  }
}
```

### Health Endpoints

| Endpoint                             | Purpose                                  |
| ------------------------------------ | ---------------------------------------- |
| `GET /api/v1/recipe-scraper/health`  | Liveness probe - service is running      |
| `GET /api/v1/recipe-scraper/ready`   | Readiness probe - dependencies available |
| `GET /api/v1/recipe-scraper/metrics` | Prometheus metrics                       |

---

## Source Files Reference

| File                               | Purpose                               |
| ---------------------------------- | ------------------------------------- |
| `src/app/factory.py`               | Application factory, middleware setup |
| `src/app/api/v1/router.py`         | API route configuration               |
| `src/app/schemas/recipe.py`        | Recipe data models                    |
| `src/app/schemas/ingredient.py`    | Ingredient models                     |
| `src/app/schemas/enums.py`         | Enumeration types                     |
| `src/app/workers/arq.py`           | ARQ worker configuration              |
| `src/app/workers/jobs.py`          | Job enqueueing functions              |
| `src/app/workers/tasks/example.py` | Background task implementations       |
| `src/app/auth/permissions.py`      | RBAC definitions                      |
| `src/app/llm/client/fallback.py`   | Fallback LLM client                   |
| `src/app/llm/prompts/base.py`      | Base prompt class                     |
| `src/app/llm/models.py`            | LLM request/response models           |
