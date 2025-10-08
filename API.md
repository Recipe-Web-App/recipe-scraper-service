# API Documentation

This document provides comprehensive information about the Recipe Scraper
Service API endpoints, request/response formats, and usage examples.

## Base Information

- **Base URL**: `http://localhost:8000/api/v1`
- **API Version**: v1
- **Content-Type**: `application/json`
- **Interactive Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Documentation**: `http://localhost:8000/redoc` (ReDoc)

## Authentication

The API supports OAuth2 authentication with JWT tokens. Authentication can
be configured to be optional or required depending on deployment settings.

### Authentication Methods

1. **JWT Token Validation** (Default)
   - Uses local JWT validation with a shared secret
   - Faster performance, no external calls required
   - Configure with `OAUTH2_INTROSPECTION_ENABLED=false`

2. **OAuth2 Token Introspection**
   - Validates tokens via external OAuth2 introspection endpoint
   - Real-time token validation and revocation support
   - Configure with `OAUTH2_INTROSPECTION_ENABLED=true`

### Authentication Headers

Include the authorization header in your requests:

```http
Authorization: Bearer <your-jwt-token>
```

### Authentication Modes

- **Optional Authentication**: Some endpoints work with or without authentication
- **Required Authentication**: Protected endpoints require valid authentication
- **Service-to-Service**: Admin endpoints require service-to-service tokens

### Authentication Errors

Authentication failures return specific error responses:

```json
{
  "detail": "Authentication required",
  "error_type": "authentication_required"
}
```

Common authentication error types:

- `authentication_required` - Missing or invalid authentication
- `invalid_token` - Token is malformed or signature invalid
- `expired_token` - Token has expired
- `insufficient_permissions` - Valid token but lacks required permissions
- `introspection_failed` - OAuth2 introspection validation failed

## Rate Limiting

- **Default Rate Limit**: 100 requests per minute per IP address
- **Rate Limit Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when rate limit window resets

## Common Response Format

All API responses follow a consistent structure:

```json
{
  "data": {},           // Response data (varies by endpoint)
  "message": "string",  // Human-readable message
  "success": true,      // Boolean indicating success/failure
  "timestamp": "2025-01-15T10:30:00Z",  // ISO 8601 timestamp
  "request_id": "uuid"  // Unique request identifier
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},       // Additional error context (optional)
    "field_errors": []   // Field validation errors (optional)
  },
  "success": false,
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "uuid"
}
```

### HTTP Status Codes

- `200` - OK: Successful request
- `201` - Created: Resource successfully created
- `400` - Bad Request: Invalid request parameters
- `404` - Not Found: Resource not found
- `422` - Unprocessable Entity: Validation error
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Server error
- `503` - Service Unavailable: Service temporarily unavailable

## Endpoints

### Health Check Endpoints

#### GET `/health`

Comprehensive health check including all dependencies.

**Response:**

```json
{
  "data": {
    "status": "healthy",
    "version": "0.1.0",
    "uptime": 3600,
    "dependencies": {
      "database": "healthy",
      "redis": "healthy",
      "spoonacular_api": "healthy"
    },
    "metrics": {
      "total_requests": 1500,
      "cache_hit_rate": 0.85,
      "average_response_time": 0.15
    }
  },
  "success": true,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### GET `/liveness`

Basic liveness probe for Kubernetes.

**Response:**

```json
{
  "data": {
    "status": "alive",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "success": true
}
```

#### GET `/readiness`

Readiness probe checking critical dependencies.

**Response:**

```json
{
  "data": {
    "status": "ready",
    "dependencies": {
      "database": "connected",
      "cache": "connected"
    }
  },
  "success": true
}
```

### Recipe Scraper Endpoints

#### POST `/recipe-scraper/create-recipe`

Create a recipe by scraping data from a URL.

**Request Body:**

```json
{
  "url": "https://example.com/recipe",
  "title": "Custom Recipe Title",        // Optional override
  "tags": ["dinner", "vegetarian"],     // Optional tags
  "difficulty_level": "medium"          // Optional: easy, medium, hard
}
```

**Response:**

```json
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Delicious Pasta Recipe",
    "description": "A wonderful pasta dish...",
    "prep_time": 15,
    "cook_time": 30,
    "servings": 4,
    "difficulty_level": "medium",
    "ingredients": [
      {
        "name": "Pasta",
        "amount": 500,
        "unit": "grams",
        "notes": "Any long pasta works"
      }
    ],
    "instructions": [
      {
        "step_number": 1,
        "instruction": "Boil water in a large pot",
        "duration": 5
      }
    ],
    "nutritional_info": {
      "calories": 420,
      "protein": 15.5,
      "carbohydrates": 65.2,
      "fat": 8.3
    },
    "source_url": "https://example.com/recipe",
    "created_at": "2025-01-15T10:30:00Z"
  },
  "success": true
}
```

#### GET `/recipe-scraper/popular-recipes`

Get a list of popular recipes from various cooking websites.

**Query Parameters:**

- `limit` (int, optional): Number of recipes to return (default: 20, max: 100)
- `offset` (int, optional): Number of recipes to skip (default: 0)
- `category` (string, optional): Recipe category filter
- `difficulty` (string, optional): Difficulty level filter

**Response:**

```json
{
  "data": {
    "recipes": [
      {
        "title": "Quick Chicken Stir Fry",
        "url": "https://example.com/chicken-stir-fry",
        "image_url": "https://example.com/image.jpg",
        "description": "Fast and healthy dinner option",
        "prep_time": 10,
        "cook_time": 15,
        "difficulty_level": "easy",
        "rating": 4.5,
        "source": "Example Cooking Blog"
      }
    ],
    "pagination": {
      "total": 500,
      "limit": 20,
      "offset": 0,
      "has_next": true,
      "has_previous": false
    }
  },
  "success": true
}
```

### Nutritional Information Endpoints

#### GET `/nutritional-info/{ingredient}`

Get nutritional information for a specific ingredient.

**Path Parameters:**

- `ingredient` (string): Name of the ingredient

**Query Parameters:**

- `amount` (float, optional): Amount of ingredient (default: 100)
- `unit` (string, optional): Unit of measurement (default: "grams")

**Response:**

```json
{
  "data": {
    "ingredient": "chicken breast",
    "amount": 100,
    "unit": "grams",
    "nutritional_info": {
      "calories": 165,
      "protein": 31.0,
      "carbohydrates": 0,
      "fat": 3.6,
      "fiber": 0,
      "sugar": 0,
      "sodium": 74,
      "vitamins": {
        "vitamin_a": 21,
        "vitamin_c": 0,
        "vitamin_d": 0.2
      },
      "minerals": {
        "calcium": 15,
        "iron": 0.9,
        "potassium": 256
      }
    },
    "classification": {
      "food_group": "protein",
      "allergens": [],
      "dietary_restrictions": ["keto-friendly", "low-carb"]
    }
  },
  "success": true
}
```

### Recommendation Endpoints

#### GET `/recommendations/substitutes`

Get ingredient substitution recommendations.

**Query Parameters:**

- `ingredient` (string, required): Original ingredient name
- `amount` (float, optional): Amount of original ingredient
- `unit` (string, optional): Unit of measurement
- `dietary_restrictions` (array, optional): Dietary restrictions to consider

**Response:**

```json
{
  "data": {
    "original_ingredient": "butter",
    "substitutes": [
      {
        "ingredient": "coconut oil",
        "ratio": 1.0,
        "confidence": 0.95,
        "notes": "Works well for baking, adds subtle coconut flavor",
        "dietary_benefits": ["dairy-free", "vegan"]
      },
      {
        "ingredient": "olive oil",
        "ratio": 0.75,
        "confidence": 0.85,
        "notes": "Better for savory dishes",
        "dietary_benefits": ["dairy-free", "vegan", "heart-healthy"]
      }
    ],
    "dietary_considerations": [
      "Consider taste profile changes",
      "Melting point differences may affect texture"
    ]
  },
  "success": true
}
```

#### GET `/recommendations/similar-recipes`

Get recommendations for similar recipes.

**Query Parameters:**

- `recipe_id` (string, optional): Recipe ID for similarity matching
- `ingredients` (array, optional): List of ingredients to match
- `cuisine` (string, optional): Cuisine type preference
- `difficulty` (string, optional): Difficulty level preference
- `max_cook_time` (int, optional): Maximum cooking time in minutes

**Response:**

```json
{
  "data": {
    "recommended_recipes": [
      {
        "id": "uuid",
        "title": "Mediterranean Pasta",
        "similarity_score": 0.85,
        "shared_ingredients": ["tomatoes", "olive oil", "garlic"],
        "prep_time": 20,
        "cook_time": 25,
        "difficulty_level": "medium",
        "rating": 4.3,
        "reason": "Similar cooking technique and ingredient profile"
      }
    ],
    "matching_criteria": {
      "ingredient_overlap": 0.75,
      "cuisine_match": true,
      "difficulty_match": true
    }
  },
  "success": true
}
```

### Admin Endpoints

#### GET `/admin/system-stats`

Get system statistics and performance metrics.

**Response:**

```json
{
  "data": {
    "system_info": {
      "version": "0.1.0",
      "uptime": 86400,
      "python_version": "3.13.1",
      "environment": "production"
    },
    "performance_metrics": {
      "total_requests": 15000,
      "requests_per_minute": 125,
      "average_response_time": 0.15,
      "cache_hit_rate": 0.85,
      "error_rate": 0.02
    },
    "resource_usage": {
      "memory_usage": 256,
      "cpu_usage": 15.5,
      "disk_usage": 45.2
    },
    "database_stats": {
      "total_recipes": 1250,
      "active_connections": 12,
      "query_performance": 0.05
    }
  },
  "success": true
}
```

#### POST `/admin/cache/clear`

Clear application cache.

**Request Body:**

```json
{
  "cache_type": "all",  // Options: "all", "redis", "memory", "files"
  "pattern": "*"        // Optional: specific cache key pattern
}
```

**Response:**

```json
{
  "data": {
    "cache_cleared": true,
    "items_removed": 1500,
    "cache_type": "all"
  },
  "success": true
}
```

## Webhook Support

### Recipe Processing Webhooks

The service can send webhook notifications when recipes are processed:

**Webhook Payload:**

```json
{
  "event": "recipe.created",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "recipe_id": "uuid",
    "title": "Recipe Title",
    "source_url": "https://example.com/recipe",
    "processing_time": 2.5,
    "success": true
  }
}
```

## SDK and Client Libraries

### Python Client Example

```python
import requests

class RecipeScraperClient:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url

    def create_recipe(self, url, **kwargs):
        response = requests.post(
            f"{self.base_url}/recipe-scraper/create-recipe",
            json={"url": url, **kwargs}
        )
        return response.json()

    def get_nutritional_info(self, ingredient, amount=100, unit="grams"):
        response = requests.get(
            f"{self.base_url}/nutritional-info/{ingredient}",
            params={"amount": amount, "unit": unit}
        )
        return response.json()

# Usage
client = RecipeScraperClient()
recipe = client.create_recipe("https://example.com/recipe")
nutrition = client.get_nutritional_info("chicken breast", 150)
```

### JavaScript/Node.js Client Example

```javascript
class RecipeScraperClient {
  constructor(baseUrl = 'http://localhost:8000/api/v1') {
    this.baseUrl = baseUrl;
  }

  async createRecipe(url, options = {}) {
    const response = await fetch(
      `${this.baseUrl}/recipe-scraper/create-recipe`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, ...options })
      }
    );
    return response.json();
  }

  async getNutritionalInfo(ingredient, amount = 100, unit = 'grams') {
    const params = new URLSearchParams({ amount, unit });
    const response = await fetch(
      `${this.baseUrl}/nutritional-info/${ingredient}?${params}`
    );
    return response.json();
  }
}

// Usage
const client = new RecipeScraperClient();
const recipe = await client.createRecipe('https://example.com/recipe');
const nutrition = await client.getNutritionalInfo('chicken breast', 150);
```

## Testing API Endpoints

### Using curl

```bash
# Create a recipe
curl -X POST "http://localhost:8000/api/v1/recipe-scraper/create-recipe" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/recipe"}'

# Get nutritional info
curl "http://localhost:8000/api/v1/nutritional-info/chicken%20breast?amount=150"

# Get popular recipes
curl "http://localhost:8000/api/v1/recipe-scraper/popular-recipes?limit=10&category=dinner"
```

### Using Postman

Import the provided Postman collection from `/postman/` directory for
comprehensive API testing with pre-configured environments and test scripts.

## API Versioning

- Current Version: `v1`
- Version specified in URL path: `/api/v1/`
- Backward compatibility maintained within major versions
- Breaking changes will increment major version: `/api/v2/`

## Performance Considerations

- **Caching**: Responses are cached for improved performance
- **Rate Limiting**: Implement client-side rate limiting for high-volume usage
- **Pagination**: Use limit/offset parameters for large datasets
- **Async Processing**: Long-running operations may return 202 Accepted with
  status endpoints

## Monitoring and Observability

- **Request Tracing**: Each request includes a unique `request_id`
- **Metrics**: Prometheus metrics available at `/metrics`
- **Health Checks**: Use health endpoints for monitoring
- **Logging**: Structured logs with correlation IDs

For more detailed implementation examples and advanced usage patterns, refer
to the [interactive API documentation](http://localhost:8000/docs) when the
service is running.
