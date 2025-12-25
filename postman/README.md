# Recipe Scraper Service - Postman Collection

This directory contains Postman collection and environment files for
comprehensive API testing of the Recipe Scraper Service.

## Files Overview

### Collection Files

- **`Recipe-Scraper-Service.postman_collection.json`** - Complete API
  collection covering all endpoints including recipe scraping, nutritional
  analysis, ingredient substitutions, shopping information, and health
  monitoring

### Environment Files

- **`Recipe-Scraper-Development.postman_environment.json`** - Development
  environment variables (passwords as placeholders)
- **`Recipe-Scraper-Local.postman_environment.json`** - Local development
  environment variables (passwords as placeholders)
- **`*-Private.postman_environment.json`** - Local-only files with real
  passwords (gitignored)

## Setup Instructions

### 1. Import Collections and Environments

1. **Import Collection:**
   - Open Postman
   - Click "Import" button
   - Select `Recipe-Scraper-Service.postman_collection.json` file
   - Collection will appear in your workspace

2. **Import Environment Templates:**
   - Import both environment files:
     `Recipe-Scraper-Development.postman_environment.json` and
     `Recipe-Scraper-Local.postman_environment.json`

### 2. Set Up Private Environment with Passwords

The environment files in Git have placeholder values for passwords. To use
them locally:

1. **Create Private Environment Files:**

   ```bash
   # Copy the environment files and add '-Private' suffix
   cp Recipe-Scraper-Development.postman_environment.json \
      Recipe-Scraper-Development-Private.postman_environment.json
   cp Recipe-Scraper-Local.postman_environment.json \
      Recipe-Scraper-Local-Private.postman_environment.json
   ```

2. **Add Real Passwords:**
   Edit your `-Private` files and replace these placeholder values:
   - `REPLACE_WITH_YOUR_AUTH_TOKEN` → Your actual authentication token
   - `REPLACE_WITH_YOUR_ADMIN_TOKEN` → Your actual admin token (if different)

3. **Import Private Environments:**
   - Import your `-Private.postman_environment.json` files into Postman
   - Use these private environments for actual testing
   - The `-Private` files are automatically gitignored

4. **Select Environment:**
   - Choose the appropriate private environment from the dropdown in
     Postman's top-right corner

## Collection Structure

### 1. Root & Monitoring

Basic service endpoints and metrics:

- **Root Endpoint** - Service information and status
- **Prometheus Metrics** - Monitoring metrics for observability

### 2. Health Checks

Comprehensive health monitoring endpoints:

- **Liveness Probe** - Basic Kubernetes liveness check
- **Readiness Probe** - Database and dependency readiness check
- **Comprehensive Health Check** - Detailed health status with all dependencies
- **Legacy Health Check (Deprecated)** - Backwards compatibility endpoint

### 3. Recipe Management

Core recipe operations:

- **Create Recipe from URL** - Scrape and create recipes from popular
  recipe websites
- **Get Popular Recipes** - Retrieve curated list of trending recipes with
  pagination

### 4. Nutritional Information

Nutritional analysis and data:

- **Get Recipe Nutritional Info** - Comprehensive nutritional breakdown
  for entire recipes
- **Get Ingredient Nutritional Info** - Detailed nutritional data for
  individual ingredients

### 5. AI-Powered Recommendations

Intelligent suggestions and substitutions:

- **Get Ingredient Substitutions** - AI-powered ingredient substitution
  recommendations with conversion ratios
- **Get Recipe Pairing Suggestions** - Recipe pairing recommendations
  based on flavor profiles

### 6. Shopping Integration

Shopping and pricing information:

- **Get Ingredient Shopping Info** - Price estimates and shopping details
  for individual ingredients
- **Get Recipe Shopping Info** - Complete shopping list with total cost
  estimates for entire recipes

### 7. Administrative Operations

Administrative endpoints requiring elevated permissions:

- **Clear Cache** - Clear service cache (requires admin authentication)

## Environment Variables

### Base URLs

- **`recipeScraperServiceBaseUrl`** - Recipe Scraper service base URL

### Authentication

- **`recipeScraperServiceAuthToken`** - Bearer token for API
  authentication (secret type)
- **`recipeScraperServiceAdminToken`** - Admin-level authentication token
  (secret type)

### Test Data Variables

- **`recipeScraperServiceTestRecipeId`** - Sample recipe ID for testing
- **`recipeScraperServiceTestIngredientId`** - Sample ingredient ID for
  testing
- **`recipeScraperServiceAllRecipesUrl`** - Sample AllRecipes URL for
  recipe creation
- **`recipeScraperServiceFoodNetworkUrl`** - Sample Food Network URL for
  recipe creation

### Auto-managed Variables

These variables are automatically set by test scripts:

- **`recipeScraperServiceCreatedRecipeId`** - Dynamically set recipe ID
  from create operations
- **`recipeScraperServiceCreatedIngredientId`** - Dynamically set
  ingredient ID from responses

## Automatic Response Field Extraction

The collection includes robust test scripts that automatically extract
important response fields and store them as environment variables for use in
subsequent requests:

### Recipe Management Flow

- Create Recipe requests automatically extract the new recipe ID for use
  in subsequent operations
- Recipe responses extract ingredient IDs for nutritional and shopping
  queries
- All requests include status code validation and response structure
  validation

### Authentication Flow

- Authentication headers are automatically applied using stored tokens
- Admin endpoints automatically use admin-level tokens when available

## Environment Switching

**Development Environment:**

- Recipe Scraper Service: `http://sous-chef-proxy.local/api/v1/recipe-scraper`

**Local Environment:**

- Recipe Scraper Service: `http://localhost:8000`

Switch between environments using the environment selector dropdown in
Postman's top-right corner.

## Security Features

- **Password Protection**: Sensitive tokens are excluded from Git
  repository
- **Private Environment Pattern**: Use local `-Private` files for
  credentials (automatically gitignored)
- **Secret Variables**: Tokens are marked as secret type in Postman
- **Automatic Token Management**: Bearer tokens are automatically applied
  through collection-level authentication
- **Environment Isolation**: Separate environments prevent accidental
  cross-environment requests

### Security Model

- **Git Repository**: Contains collections and environment templates with
  placeholder tokens
- **Local Development**: Uses private environment files with real
  credentials
- **Team Collaboration**: Secure sharing of API structure without exposing
  credentials

## API Features Covered

### Recipe Scraping

- **URL Support**: AllRecipes, Food Network, and other popular recipe
  sites
- **Data Extraction**: Title, description, ingredients, cooking steps,
  timing, and difficulty
- **Validation**: URL validation and error handling for unsupported sites

### Nutritional Analysis

- **Comprehensive Data**: Macronutrients, vitamins, minerals, allergens
- **Serving Adjustments**: Scale nutritional data based on custom quantities
- **Aggregation**: Total nutritional values for complete recipes

### AI Recommendations

- **Ingredient Substitutions**: Smart substitutions with conversion ratios
- **Recipe Pairings**: AI-powered recipe pairing suggestions
- **Dietary Considerations**: Allergen and dietary restriction awareness

### Shopping Integration

- **Price Estimates**: Current pricing data for ingredients
- **Quantity Conversion**: Convert between different units of measurement
- **Total Cost Calculation**: Complete recipe cost estimation

### Health Monitoring

- **Service Health**: Comprehensive health checks including database,
  cache, and external APIs
- **Metrics**: Prometheus-compatible metrics for monitoring and alerting
- **Kubernetes Ready**: Liveness and readiness probes for container
  orchestration

## Usage Workflow

### Getting Started

1. Import collection file and environment templates
2. Set up private environment files with real authentication tokens (see
   setup instructions above)
3. Select appropriate private environment (Development-Private or
   Local-Private)
4. Start with health checks to verify service connectivity
5. Use recipe creation to generate test data
6. Explore nutritional, recommendation, and shopping features
7. Test admin operations if you have admin privileges

### Typical Testing Flow

1. **Health Check** - Verify service is running and healthy
2. **Create Recipe** - Scrape a recipe from a popular site to generate
   test data
3. **Nutritional Analysis** - Get nutritional breakdown for the created
   recipe
4. **Ingredient Substitutions** - Find alternatives for specific
   ingredients
5. **Recipe Pairings** - Get complementary recipe suggestions
6. **Shopping Information** - Get pricing and shopping details
7. **Admin Operations** - Clear cache or perform maintenance (if
   authorized)

## Test Script Features

All requests include comprehensive test scripts that:

- Validate HTTP status codes
- Check response structure and required fields
- Extract and store important response data as environment variables
- Provide clear test result feedback
- Enable request chaining through automatic variable management

## Error Handling

The collection includes comprehensive error scenarios:

- **400 Bad Request** - Invalid URLs, missing parameters
- **401 Unauthorized** - Missing or invalid authentication
- **403 Forbidden** - Insufficient permissions for admin operations
- **404 Not Found** - Non-existent recipes or ingredients
- **422 Unprocessable Entity** - Validation errors
- **503 Service Unavailable** - Service health issues

## Future Enhancements

The collection is designed for expansion and will include:

- Meal planning and recipe scheduling
- User preference learning and personalization
- Advanced dietary restriction filtering
- Recipe rating and review system
- Social features for recipe sharing
- Bulk operations for recipe management

This collection provides a foundation for comprehensive API testing with
automatic token management, response validation, and seamless request
chaining for the Recipe Scraper Service.
