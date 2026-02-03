# Shopping Information Feature

This document explains the shopping/pricing information lookup and aggregation system, which provides estimated grocery
costs for ingredients and recipes using USDA pricing data.

## Table of Contents

1. [Overview](#1-overview)
2. [API Endpoints](#2-api-endpoints)
3. [Processing Flow](#3-processing-flow)
4. [Two-Tier Pricing Strategy](#4-two-tier-pricing-strategy)
5. [Unit Conversion](#5-unit-conversion)
6. [Caching Strategy](#6-caching-strategy)
7. [Database Schema](#7-database-schema)
8. [Error Handling](#8-error-handling)
9. [Data Attribution](#9-data-attribution)

---

## 1. Overview

The shopping information feature provides estimated grocery costs for both individual ingredients and complete recipes.
The system uses a two-tier pricing lookup strategy with USDA pricing data, falling back to food group averages when
direct ingredient pricing is unavailable.

### High-Level Architecture

```mermaid
graph TB
    subgraph Client
        C[Client Application]
    end

    subgraph "Recipe Scraper Service"
        subgraph "API Layer"
            INGR_EP["/ingredients/{id}/shopping-info"]
            RECIPE_EP["/recipes/{id}/shopping-info"]
        end

        subgraph "Service Layer"
            SS[ShoppingService]
            UC[UnitConverter]
        end

        subgraph "Data Access"
            PR[PricingRepository]
        end
    end

    subgraph "Data Stores"
        REDIS[(Redis Cache<br/>TTL: 24 hours)]
        PG[(PostgreSQL<br/>Pricing Data)]
    end

    subgraph "External"
        RMS[Recipe Management<br/>Service]
    end

    C -->|GET| INGR_EP
    C -->|GET| RECIPE_EP
    RECIPE_EP -->|Fetch Recipe| RMS
    INGR_EP --> SS
    RECIPE_EP --> SS
    SS -->|Convert Units| UC
    SS -->|Cache Lookup| REDIS
    SS -->|DB Query| PR
    PR --> PG
    UC -->|Portion Weights| PR
```

### Key Components

| Component         | Purpose                                                      |
| ----------------- | ------------------------------------------------------------ |
| ShoppingService   | Orchestrates caching, conversion, and pricing calculations   |
| UnitConverter     | Converts between measurement units using Pint library        |
| PricingRepository | PostgreSQL access for ingredient and food group pricing data |
| Redis Cache       | 24-hour caching of computed pricing responses                |

### Pricing Tiers

| Tier | Source                    | Confidence | Description                          |
| ---- | ------------------------- | ---------- | ------------------------------------ |
| 1    | Direct Ingredient Pricing | 0.95       | Exact price per gram for ingredient  |
| 2    | Food Group Average        | 0.60       | Average price for ingredient's group |

---

## 2. API Endpoints

### Ingredient Shopping Info

**Endpoint:** `GET /api/v1/recipe-scraper/ingredients/{ingredient_id}/shopping-info`

Retrieves pricing data for a single ingredient with optional quantity scaling.

| Parameter     | Type  | Required | Description                                  |
| ------------- | ----- | -------- | -------------------------------------------- |
| ingredient_id | int   | Yes      | Ingredient database identifier               |
| amount        | float | No       | Quantity amount (must be with measurement)   |
| measurement   | enum  | No       | Unit of measurement (G, KG, CUP, TBSP, etc.) |

**Response (200 OK):**

```json
{
  "ingredientName": "flour",
  "quantity": { "amount": 250.0, "measurement": "G" },
  "estimatedPrice": "0.45",
  "priceConfidence": 0.95,
  "dataSource": "USDA_FVP",
  "currency": "USD"
}
```

**Notes:**

- If no quantity is provided, returns price for 100 grams
- Both `amount` and `measurement` must be provided together, or neither

### Recipe Shopping Info

**Endpoint:** `GET /api/v1/recipe-scraper/recipes/{recipeId}/shopping-info`

Aggregates pricing data for all ingredients in a recipe.

| Parameter | Type | Required | Description       |
| --------- | ---- | -------- | ----------------- |
| recipeId  | int  | Yes      | Recipe identifier |

**Response Codes:**

- **200 OK** - All ingredients have pricing data
- **206 Partial Content** - Some ingredients missing prices (X-Partial-Content header lists missing IDs)
- **404 Not Found** - Recipe not found
- **503 Service Unavailable** - Recipe Management Service unavailable

**Response (200 OK):**

```json
{
  "recipeId": 123,
  "ingredients": {
    "flour": {
      "ingredientName": "flour",
      "quantity": { "amount": 250.0, "measurement": "G" },
      "estimatedPrice": "0.45",
      "priceConfidence": 0.95,
      "dataSource": "USDA_FVP",
      "currency": "USD"
    },
    "butter": {
      "ingredientName": "butter",
      "quantity": { "amount": 227.0, "measurement": "G" },
      "estimatedPrice": "3.50",
      "priceConfidence": 0.95,
      "dataSource": "USDA_FVP",
      "currency": "USD"
    }
  },
  "totalEstimatedCost": "3.95",
  "missingIngredients": null
}
```

**Response (206 Partial Content):**

```http
HTTP/1.1 206 Partial Content
X-Partial-Content: 105,108
```

```json
{
  "recipeId": 123,
  "ingredients": {...},
  "totalEstimatedCost": "2.50",
  "missingIngredients": [105, 108]
}
```

---

## 3. Processing Flow

### Single Ingredient Lookup

```mermaid
sequenceDiagram
    participant C as Client
    participant EP as Endpoint
    participant SS as ShoppingService
    participant RC as Redis Cache
    participant UC as UnitConverter
    participant PR as PricingRepository
    participant DB as PostgreSQL

    C->>EP: GET /ingredients/101/shopping-info?amount=1&measurement=CUP
    EP->>EP: Validate params (amount + measurement together)
    EP->>SS: get_ingredient_shopping_info(101, {1, CUP})

    SS->>RC: GET shopping:101:1.0:CUP
    alt Cache Hit
        RC-->>SS: Cached IngredientShoppingInfoResponse
    else Cache Miss
        RC-->>SS: null

        SS->>PR: get_ingredient_details(101)
        PR->>DB: SELECT name, food_group FROM ingredients
        DB-->>PR: {name: "flour", food_group: "GRAINS"}
        PR-->>SS: Ingredient details

        SS->>UC: to_grams({1, CUP}, "flour")
        UC->>PR: get_portion_weight("flour", "CUP")
        PR->>DB: SELECT gram_weight FROM ingredient_portions
        DB-->>PR: 125.0g
        UC-->>SS: 125.0 grams

        SS->>PR: get_ingredient_pricing(101)
        PR->>DB: Tier 1: SELECT price_per_gram FROM ingredient_pricing
        alt Tier 1: Direct Pricing Found
            DB-->>PR: price_per_gram, data_source
            PR-->>SS: PricingData (confidence: 0.95)
        else Tier 2: Food Group Fallback
            DB-->>PR: null
            SS->>PR: get_food_group_pricing("GRAINS")
            PR->>DB: SELECT avg_price_per_gram FROM food_group_pricing
            DB-->>PR: avg_price_per_gram
            PR-->>SS: PricingData (confidence: 0.60)
        end

        SS->>SS: Calculate: price = grams × price_per_gram
        SS->>RC: SETEX shopping:101:1.0:CUP (TTL: 24h)
    end

    SS-->>EP: IngredientShoppingInfoResponse
    EP-->>C: 200 OK + JSON
```

### Recipe Aggregation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant EP as Endpoint
    participant RMS as Recipe Management Service
    participant SS as ShoppingService
    participant RC as Redis Cache
    participant PR as PricingRepository

    C->>EP: GET /recipes/123/shopping-info
    EP->>RMS: GET /recipes/123
    RMS-->>EP: Recipe with ingredients list

    EP->>SS: get_recipe_shopping_info(123, [ingredients])

    loop For each ingredient
        SS->>SS: get_ingredient_shopping_info(id, quantity)
        Note over SS: Two-tier lookup per ingredient
    end

    SS->>SS: Sum prices for totalEstimatedCost
    SS->>SS: Collect missing ingredients

    SS-->>EP: RecipeShoppingInfoResponse

    alt All ingredients have prices
        EP-->>C: 200 OK
    else Some ingredients missing prices
        EP-->>C: 206 Partial Content + X-Partial-Content header
    end
```

---

## 4. Two-Tier Pricing Strategy

The ShoppingService uses a two-tier approach to maximize pricing data availability while indicating confidence levels.

```mermaid
flowchart TD
    START[Ingredient Query] --> CACHE{Cache<br/>Lookup}

    CACHE -->|Hit| RETURN[Return Cached Data]
    CACHE -->|Miss| CONVERT[Convert to Grams]

    CONVERT --> TIER1{Tier 1:<br/>Direct Pricing?}

    TIER1 -->|Yes| CALC1[Calculate Price<br/>Confidence: 0.95]
    TIER1 -->|No| TIER2{Tier 2:<br/>Food Group Pricing?}

    TIER2 -->|Yes| CALC2[Calculate Price<br/>Confidence: 0.60]
    TIER2 -->|No| NO_PRICE[Return null price]

    CALC1 --> CACHE_STORE[Cache & Return]
    CALC2 --> CACHE_STORE
    NO_PRICE --> MARK_MISSING[Mark as Missing]

    CACHE_STORE --> RETURN
    MARK_MISSING --> RETURN

    style TIER1 fill:#90EE90
    style TIER2 fill:#F0E68C
    style NO_PRICE fill:#FFB6C1
```

### Confidence Scores

| Tier | Confidence | Description                                        |
| ---- | ---------- | -------------------------------------------------- |
| 1    | 0.95       | Direct ingredient pricing - highly accurate        |
| 2    | 0.60       | Food group average - less accurate but informative |
| -    | null       | No pricing data available                          |

### Data Sources

| Source    | Description                              |
| --------- | ---------------------------------------- |
| USDA_FVP  | USDA Fruit and Vegetable Prices          |
| USDA_FMAP | USDA Food Marketing and Analysis Program |

---

## 5. Unit Conversion

The UnitConverter converts ingredient quantities to grams for price calculation using a three-tier strategy:

```mermaid
flowchart TD
    START[Receive Quantity] --> CHECK{What type<br/>of unit?}

    CHECK -->|Weight Unit<br/>G, KG, OZ, LB| PINT[Pint Library<br/>Direct Conversion]
    PINT --> DONE[Return Grams]

    CHECK -->|Volume Unit<br/>CUP, TBSP, TSP, ML, L| VOL_DB[DB: Get Portion Weight]
    VOL_DB --> VOL_FOUND{Found?}
    VOL_FOUND -->|Yes| DONE
    VOL_FOUND -->|No| VOL_FALL[Fallback: 1 g/ml density]
    VOL_FALL --> DONE

    CHECK -->|Count Unit<br/>PIECE, CLOVE, etc.| COUNT_DB[DB: Get Portion Weight]
    COUNT_DB --> COUNT_FOUND{Found?}
    COUNT_FOUND -->|Yes| DONE
    COUNT_FOUND -->|No| COUNT_ERR[Raise ConversionError]

    style PINT fill:#90EE90
    style VOL_FALL fill:#FFE4B5
    style COUNT_ERR fill:#FFB6C1
```

### Supported Units

| Category | Units                        | Conversion Method            |
| -------- | ---------------------------- | ---------------------------- |
| Weight   | G, KG, OZ, LB                | Direct Pint conversion       |
| Volume   | CUP, TBSP, TSP, ML, L, FL_OZ | DB lookup → 1 g/ml fallback  |
| Count    | PIECE, CLOVE, SLICE, etc.    | DB lookup → Error if missing |

---

## 6. Caching Strategy

```mermaid
flowchart TB
    subgraph "Cache Layer"
        direction TB
        KEY["Cache Key: shopping:{ingredient_id}:{amount}:{unit}"]
        TTL["TTL: 24 hours (86,400 seconds)"]
        DATA["Stores: Complete IngredientShoppingInfoResponse"]
    end

    subgraph "Cache Flow"
        direction LR
        REQ[Request] --> LOOKUP[Cache Lookup]
        LOOKUP -->|Hit| RESPONSE[Response]
        LOOKUP -->|Miss| CALC[Calculate Price]
        CALC --> CACHE_SET[Cache Response]
        CACHE_SET --> RESPONSE
    end

    style KEY fill:#E6E6FA
    style TTL fill:#E6E6FA
    style DATA fill:#E6E6FA
```

### Key Design Decisions

1. **Computed Response Caching**: Cache stores the complete response including calculated price

   - Different quantities result in different cache entries
   - Avoids recalculation for repeated identical requests

2. **24-hour TTL**: Shorter than nutrition (30 days) because:

   - Prices are more volatile than nutritional data
   - Still provides significant performance benefit

3. **Graceful Degradation**: Cache failures don't fail requests
   - Falls back to direct database calculation
   - Errors logged but not propagated

### Cache Key Format

```text
shopping:{ingredient_id}:{amount}:{unit}

Examples:
- shopping:101:100.0:G
- shopping:101:1.0:CUP
- shopping:102:2.0:TBSP
```

---

## 7. Database Schema

```mermaid
erDiagram
    ingredients ||--o| ingredient_pricing : has
    ingredients ||--o| nutrition_profiles : has
    nutrition_profiles ||--|| food_group_pricing : references
    ingredients ||--o{ ingredient_portions : has

    ingredients {
        bigint ingredient_id PK
        varchar name UK
        int fdc_id
        text usda_food_description
    }

    nutrition_profiles {
        bigint nutrition_profile_id PK
        bigint ingredient_id FK
        varchar food_group "GRAINS, DAIRY, etc."
        decimal serving_size_g
    }

    ingredient_pricing {
        bigint pricing_id PK
        bigint ingredient_id FK "UNIQUE"
        decimal price_per_gram
        varchar data_source "USDA_FVP, USDA_FMAP"
        timestamp updated_at
    }

    food_group_pricing {
        bigint food_group_pricing_id PK
        varchar food_group UK "GRAINS, DAIRY, etc."
        decimal avg_price_per_gram
        varchar data_source
        timestamp updated_at
    }

    ingredient_portions {
        bigint id PK
        bigint ingredient_id FK
        varchar portion_description
        varchar unit
        decimal gram_weight
    }
```

### Query Patterns

**Tier 1 - Direct Ingredient Pricing:**

```sql
SELECT price_per_gram, data_source
FROM recipe_manager.ingredient_pricing
WHERE ingredient_id = $1
```

**Tier 2 - Food Group Fallback:**

```sql
SELECT fgp.avg_price_per_gram, fgp.data_source
FROM recipe_manager.food_group_pricing fgp
JOIN recipe_manager.nutrition_profiles np
    ON fgp.food_group = np.food_group
WHERE np.ingredient_id = $1
```

---

## 8. Error Handling

### Error Codes Reference

| HTTP Status | Error Code              | Scenario                                         |
| ----------- | ----------------------- | ------------------------------------------------ |
| 200         | -                       | Success - all pricing data found                 |
| 206         | -                       | Partial Content - some ingredients missing price |
| 400         | INVALID_QUANTITY_PARAMS | Only amount or only measurement provided         |
| 404         | INGREDIENT_NOT_FOUND    | Ingredient not in database                       |
| 422         | CONVERSION_ERROR        | Unit conversion failed (e.g., PIECE without DB)  |
| 503         | SERVICE_UNAVAILABLE     | Recipe Management Service unavailable            |

### Error Response Format

```json
{
  "error": "HTTP_ERROR",
  "message": "{'error': 'INVALID_QUANTITY_PARAMS', 'message': 'Both amount and measurement must be provided together'}",
  "details": null,
  "request_id": "abc-123"
}
```

### Partial Content Response

When recipe aggregation encounters ingredients without pricing:

```http
HTTP/1.1 206 Partial Content
X-Partial-Content: 103,105

{
  "recipeId": 123,
  "ingredients": {...},
  "totalEstimatedCost": "5.25",
  "missingIngredients": [103, 105]
}
```

The `X-Partial-Content` header contains comma-separated ingredient IDs that could not be priced.

---

## 9. Data Attribution

Pricing information in this service is derived from USDA data sources:

> **U.S. Department of Agriculture, Economic Research Service.**
>
> - Fruit and Vegetable Prices (FVP)
> - Food Marketing and Analysis Program (FMAP)

### Notes on Pricing Data

- Prices are estimates based on national averages
- Actual grocery prices vary by location, season, and retailer
- Food group averages provide rough estimates when direct pricing unavailable
- Currency is USD; international pricing not currently supported

### Data Freshness

- Pricing data is updated periodically from USDA sources
- Cache TTL of 24 hours balances freshness with performance
- `updated_at` timestamps track when pricing data was last refreshed
