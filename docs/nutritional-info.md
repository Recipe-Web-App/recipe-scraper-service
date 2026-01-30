# Nutritional Information Feature

This document explains the nutritional information lookup and aggregation system, which provides USDA FoodData Central
nutritional data for ingredients and recipes.

## Table of Contents

1. [Overview](#1-overview)
2. [API Endpoints](#2-api-endpoints)
3. [Processing Flow](#3-processing-flow)
4. [Unit Conversion](#4-unit-conversion)
5. [Caching Strategy](#5-caching-strategy)
6. [Database Schema](#6-database-schema)
7. [Error Handling](#7-error-handling)
8. [Data Attribution](#8-data-attribution)

---

## 1. Overview

The nutritional information feature provides comprehensive nutritional data including macronutrients, vitamins, and
minerals for both individual ingredients and complete recipes. Data is sourced from the USDA FoodData Central database.

### High-Level Architecture

```mermaid
graph TB
    subgraph Client
        C[Client Application]
    end

    subgraph "Recipe Scraper Service"
        subgraph "API Layer"
            INGR_EP["/ingredients/{id}/nutritional-info"]
            RECIPE_EP["/recipes/{id}/nutritional-info"]
        end

        subgraph "Service Layer"
            NS[NutritionService]
            UC[UnitConverter]
        end

        subgraph "Data Access"
            NR[NutritionRepository]
        end
    end

    subgraph "Data Stores"
        REDIS[(Redis Cache<br/>TTL: 30 days)]
        PG[(PostgreSQL<br/>Nutrition Data)]
    end

    subgraph "External"
        RMS[Recipe Management<br/>Service]
    end

    C -->|GET| INGR_EP
    C -->|GET| RECIPE_EP
    RECIPE_EP -->|Fetch Recipe| RMS
    INGR_EP --> NS
    RECIPE_EP --> NS
    NS -->|Convert Units| UC
    NS -->|Cache Lookup| REDIS
    NS -->|DB Query| NR
    NR --> PG
    UC -->|Portion Weights| NR
```

### Key Components

| Component           | Purpose                                                    |
| ------------------- | ---------------------------------------------------------- |
| NutritionService    | Orchestrates caching, conversion, and database operations  |
| UnitConverter       | Converts between measurement units using Pint library      |
| NutritionRepository | PostgreSQL access for nutritional data and portion weights |
| Redis Cache         | 30-day caching of raw nutritional data per ingredient      |

---

## 2. API Endpoints

### Ingredient Nutritional Info

**Endpoint:** `GET /ingredients/{ingredient_id}/nutritional-info`

Retrieves nutritional data for a single ingredient with optional quantity scaling.

| Parameter     | Type   | Required | Description                                  |
| ------------- | ------ | -------- | -------------------------------------------- |
| ingredient_id | string | Yes      | Ingredient name/identifier                   |
| amount        | float  | No       | Quantity amount (must be with measurement)   |
| measurement   | enum   | No       | Unit of measurement (G, KG, CUP, TBSP, etc.) |

**Response (200 OK):**

```json
{
  "quantity": {"amount": 100.0, "measurement": "G"},
  "usdaFoodDescription": "Flour, wheat, all-purpose, enriched",
  "macroNutrients": {
    "calories": {"amount": 364.0, "measurement": "KILOCALORIE"},
    "carbs": {"amount": 76.3, "measurement": "GRAM"},
    "protein": {"amount": 10.3, "measurement": "GRAM"},
    "fats": {"total": {"amount": 1.0, "measurement": "GRAM"}}
  },
  "vitamins": {...},
  "minerals": {...}
}
```

### Recipe Nutritional Info

**Endpoint:** `GET /recipes/{recipeId}/nutritional-info`

Aggregates nutritional data for all ingredients in a recipe.

| Parameter          | Type | Required | Default | Description                      |
| ------------------ | ---- | -------- | ------- | -------------------------------- |
| recipeId           | int  | Yes      | -       | Recipe identifier                |
| includeTotal       | bool | No       | true    | Include aggregated totals        |
| includeIngredients | bool | No       | false   | Include per-ingredient breakdown |

**Response Codes:**

- **200 OK** - All ingredients found
- **206 Partial Content** - Some ingredients missing (X-Partial-Content header lists missing IDs)

```json
{
  "total": {
    "quantity": {"amount": 350.0, "measurement": "G"},
    "macroNutrients": {"calories": {"amount": 1297.0, "measurement": "KILOCALORIE"}}
  },
  "ingredients": {
    "101": {"quantity": {...}, "macroNutrients": {...}},
    "102": {"quantity": {...}, "macroNutrients": {...}}
  },
  "missingIngredients": [103]
}
```

---

## 3. Processing Flow

### Single Ingredient Lookup

```mermaid
sequenceDiagram
    participant C as Client
    participant EP as Endpoint
    participant NS as NutritionService
    participant RC as Redis Cache
    participant UC as UnitConverter
    participant NR as NutritionRepository
    participant DB as PostgreSQL

    C->>EP: GET /ingredients/flour/nutritional-info?amount=1&measurement=CUP
    EP->>EP: Validate params (amount + measurement together)
    EP->>NS: get_ingredient_nutrition("flour", {1, CUP})

    NS->>RC: GET nutrition:flour
    alt Cache Hit
        RC-->>NS: Cached NutritionData (per 100g)
    else Cache Miss
        RC-->>NS: null
        NS->>NR: get_by_ingredient_name("flour")
        NR->>DB: SELECT with JOINs
        DB-->>NR: Raw nutrition data
        NR-->>NS: NutritionData
        NS->>RC: SET nutrition:flour (TTL: 30 days)
    end

    NS->>UC: to_grams({1, CUP}, "flour")
    UC->>NR: get_portion_weight("flour", "CUP")
    NR->>DB: SELECT from ingredient_portions
    DB-->>NR: 125.0g
    NR-->>UC: gram_weight
    UC-->>NS: 125.0 grams

    NS->>NS: Scale nutrients by (125/100)
    NS-->>EP: IngredientNutritionalInfoResponse
    EP-->>C: 200 OK + JSON
```

### Recipe Aggregation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant EP as Endpoint
    participant RMS as Recipe Management Service
    participant NS as NutritionService
    participant RC as Redis Cache
    participant NR as NutritionRepository

    C->>EP: GET /recipes/123/nutritional-info?includeIngredients=true
    EP->>RMS: GET /recipes/123
    RMS-->>EP: Recipe with ingredients list

    EP->>NS: get_recipe_nutrition([{flour, 250g}, {sugar, 100g}])

    loop For each ingredient
        NS->>RC: GET nutrition:{name}
        alt Cache Hit
            RC-->>NS: Cached data
        else Cache Miss
            NS->>NR: get_by_ingredient_name(name)
            NR-->>NS: NutritionData
            NS->>RC: SET nutrition:{name}
        end
        NS->>NS: Scale by quantity
    end

    NS->>NS: Aggregate totals
    NS-->>EP: RecipeNutritionalInfoResponse

    alt All ingredients found
        EP-->>C: 200 OK
    else Some ingredients missing
        EP-->>C: 206 Partial Content + X-Partial-Content header
    end
```

---

## 4. Unit Conversion

The UnitConverter uses a three-tier strategy to convert measurements to grams:

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

### Portion Weight Database

The `ingredient_portions` table stores weight equivalents:

```text
| ingredient | portion_description | unit   | gram_weight |
|------------|---------------------|--------|-------------|
| flour      | 1 cup               | CUP    | 125.0       |
| butter     | 1 tablespoon        | TBSP   | 14.2        |
| eggs       | 1 large             | PIECE  | 50.0        |
```

---

## 5. Caching Strategy

```mermaid
flowchart TB
    subgraph "Cache Layer"
        direction TB
        KEY["Cache Key: nutrition:{ingredient_name}"]
        TTL["TTL: 30 days (2,592,000 seconds)"]
        DATA["Stores: Raw NutritionData per 100g"]
    end

    subgraph "Cache Flow"
        direction LR
        REQ[Request] --> LOOKUP[Cache Lookup]
        LOOKUP -->|Hit| SCALE[Scale to Quantity]
        LOOKUP -->|Miss| DB_FETCH[Fetch from DB]
        DB_FETCH --> CACHE_SET[Cache Raw Data]
        CACHE_SET --> SCALE
        SCALE --> RESPONSE[Response]
    end

    style KEY fill:#E6E6FA
    style TTL fill:#E6E6FA
    style DATA fill:#E6E6FA
```

### Key Design Decisions

1. **Raw Data Caching**: Cache stores per-100g values, not scaled values

   - Enables reuse across different quantity requests
   - Scaling is inexpensive at response time

2. **Long TTL**: 30-day expiration for nutritional data

   - USDA data changes infrequently
   - Reduces database load significantly

3. **Graceful Degradation**: Cache failures don't fail requests
   - Falls back to direct database access
   - Errors logged but not propagated

---

## 6. Database Schema

```mermaid
erDiagram
    ingredients ||--o| nutrition_profiles : has
    nutrition_profiles ||--o| macronutrients : contains
    nutrition_profiles ||--o| vitamins : contains
    nutrition_profiles ||--o| minerals : contains
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
        decimal serving_size_g
        varchar data_source
    }

    macronutrients {
        bigint macronutrient_id PK
        bigint nutrition_profile_id FK
        decimal calories_kcal
        decimal protein_g
        decimal carbs_g
        decimal fat_g
        decimal saturated_fat_g
        decimal fiber_g
        decimal sugar_g
        decimal cholesterol_mg
        decimal sodium_mg
    }

    vitamins {
        bigint vitamin_id PK
        bigint nutrition_profile_id FK
        decimal vitamin_a_mcg
        decimal vitamin_c_mcg
        decimal vitamin_d_mcg
        decimal vitamin_b6_mcg
        decimal vitamin_b12_mcg
    }

    minerals {
        bigint mineral_id PK
        bigint nutrition_profile_id FK
        decimal calcium_mg
        decimal iron_mg
        decimal magnesium_mg
        decimal potassium_mg
        decimal zinc_mg
    }

    ingredient_portions {
        bigint id PK
        bigint ingredient_id FK
        varchar portion_description
        varchar unit
        varchar modifier
        decimal gram_weight
    }
```

### Query Pattern

The repository uses LEFT JOINs to handle ingredients with partial nutritional data:

```sql
SELECT i.*, np.*, m.*, v.*, mn.*
FROM recipe_manager.ingredients i
LEFT JOIN recipe_manager.nutrition_profiles np ON i.ingredient_id = np.ingredient_id
LEFT JOIN recipe_manager.macronutrients m ON np.nutrition_profile_id = m.nutrition_profile_id
LEFT JOIN recipe_manager.vitamins v ON np.nutrition_profile_id = v.nutrition_profile_id
LEFT JOIN recipe_manager.minerals mn ON np.nutrition_profile_id = mn.nutrition_profile_id
WHERE LOWER(i.name) = LOWER($1)
```

---

## 7. Error Handling

### Error Codes Reference

| HTTP Status | Error Code              | Scenario                                   |
| ----------- | ----------------------- | ------------------------------------------ |
| 200         | -                       | Success - all data found                   |
| 206         | -                       | Partial Content - some ingredients missing |
| 400         | INVALID_QUANTITY_PARAMS | Only amount or only measurement provided   |
| 404         | INGREDIENT_NOT_FOUND    | Ingredient not in database                 |
| 422         | CONVERSION_ERROR        | Unit conversion failed                     |
| 502         | DOWNSTREAM_ERROR        | Recipe Management Service error            |
| 503         | SERVICE_UNAVAILABLE     | Recipe Management Service unavailable      |

### Error Response Format

```json
{
  "error": "INGREDIENT_NOT_FOUND",
  "message": "No nutritional data found for ingredient: unicorn-meat"
}
```

### Partial Content Response

When recipe aggregation encounters missing ingredients:

```http
HTTP/1.1 206 Partial Content
X-Partial-Content: 103,105

{
  "total": {...},
  "ingredients": {...},
  "missingIngredients": [103, 105]
}
```

---

## 8. Data Attribution

All nutritional information in this service is sourced from the USDA FoodData Central database:

> **U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, 2019. fdc.nal.usda.gov.**

For more information about the data source, visit [FoodData Central](https://fdc.nal.usda.gov/).

### FDC IDs

Each ingredient is linked to a USDA FDC ID for traceability:

- The `fdc_id` column in the ingredients table stores this reference
- The `usda_food_description` field provides the official USDA food name
