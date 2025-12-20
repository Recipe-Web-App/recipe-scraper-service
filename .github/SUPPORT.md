# Support

Thank you for using the Recipe Scraper Service! This document provides
guidance on getting help and finding resources.

## Table of Contents

- [Documentation](#documentation)
- [Getting Help](#getting-help)
- [GitHub Discussions](#github-discussions)
- [GitHub Issues](#github-issues)
- [Security Issues](#security-issues)
- [Common Questions](#common-questions)
- [Response Times](#response-times)
- [Community Guidelines](#community-guidelines)
- [Bug Report Best Practices](#bug-report-best-practices)
- [Additional Resources](#additional-resources)

## Documentation

Start with our comprehensive documentation:

- **[README.md](../README.md)** - Project overview, features, and quick start guide
- **[API.md](../API.md)** - Complete API reference with examples and client code
- **[DEPLOYMENT.md](../DEPLOYMENT.md)** - Production deployment strategies and configurations
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow and coding standards
- **[SECURITY.md](SECURITY.md)** - Security policies and vulnerability reporting
- **[CLAUDE.md](../CLAUDE.md)** - Development commands and architecture overview
- **[CHANGELOG.md](../CHANGELOG.md)** - Release history and changes

## Getting Help

Choose the appropriate support channel based on your needs:

```text
┌─────────────────────────────────┬──────────────────────────┐
│ Question Type                   │ Support Channel          │
├─────────────────────────────────┼──────────────────────────┤
│ General questions               │ GitHub Discussions       │
│ Feature requests                │ GitHub Issues            │
│ Bug reports                     │ GitHub Issues            │
│ Security vulnerabilities        │ Security Advisories      │
│ Setup/configuration help        │ GitHub Discussions       │
│ API usage questions             │ GitHub Discussions       │
│ Performance issues              │ GitHub Issues            │
│ Documentation issues            │ GitHub Issues            │
└─────────────────────────────────┴──────────────────────────┘
```

### Quick Decision Tree

1. **Is it a security vulnerability?**
   - YES → Use [GitHub Security Advisories](#security-issues)
   - NO → Continue to step 2

2. **Do you have a question or need clarification?**
   - YES → Use [GitHub Discussions](#github-discussions)
   - NO → Continue to step 3

3. **Have you found a bug or want to request a feature?**
   - YES → Use [GitHub Issues](#github-issues)
   - NO → Check [Common Questions](#common-questions)

## GitHub Discussions

**Best for**: Questions, ideas, and community conversations

### When to Use Discussions

- Questions about using the service
- Setup and configuration help
- API usage questions
- Ideas for new features (before creating a formal feature request)
- Sharing your integrations and use cases
- General discussions about the project

### Discussion Categories

- **Q&A** - Ask questions and get help from the community
- **Ideas** - Share ideas for new features or improvements
- **Show and Tell** - Share your integrations and implementations
- **General** - Other discussions about the project

### Creating a Discussion

1. Visit [Discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions)
2. Click "New discussion"
3. Choose the appropriate category
4. Write a clear title and description
5. Submit your discussion

## GitHub Issues

**Best for**: Bug reports, feature requests, and actionable items

### When to Use Issues

- Reporting bugs or unexpected behavior
- Requesting new features
- Reporting performance problems
- Reporting documentation issues
- Proposing changes or improvements

### Issue Templates

We provide structured templates for different types of issues:

- **Bug Report** - Report unexpected behavior or errors
- **Feature Request** - Propose new features or enhancements
- **Performance Issue** - Report performance degradation or optimization opportunities
- **Documentation** - Report documentation issues or improvements
- **Task** - Track development tasks and implementation work
- **Security Vulnerability** - Report low-severity security issues (use
  Security Advisories for high/critical)

### Creating an Issue

1. Visit [Issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues)
2. Click "New issue"
3. Choose the appropriate template
4. Fill out all required fields
5. Submit your issue

## Security Issues

**IMPORTANT**: Do NOT create public issues for security vulnerabilities.

### For Security Vulnerabilities

Use **GitHub Security Advisories**:

- Go to <https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new>
- Provide details about the vulnerability
- We will respond within 48 hours

See [SECURITY.md](SECURITY.md) for complete security reporting guidelines.

## Common Questions

### Setup and Configuration

**Q: How do I install and run the service locally?**

A: Follow these steps:

```bash
# Clone the repository
git clone https://github.com/Recipe-Web-App/recipe-scraper-service.git
cd recipe-scraper-service

# Install dependencies
poetry install

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the service
poetry run dev
```

See [README.md](../README.md) for detailed setup instructions.

**Q: What environment variables do I need to configure?**

A: Essential environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string (optional, for caching)
- `SPOONACULAR_API_KEY` - Spoonacular API key for nutritional data
- `SECRET_KEY` - Secret key for security features

See `.env.example` for a complete list and [DEPLOYMENT.md](../DEPLOYMENT.md)
for production configuration.

**Q: How do I get a Spoonacular API key?**

A: Visit <https://spoonacular.com/food-api> to sign up for a free or paid API key.

### Using the API

**Q: How do I scrape a recipe from a URL?**

A: Make a POST request to `/api/v1/recipes/scrape`:

```bash
curl -X POST "http://localhost:8000/api/v1/recipes/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/recipe"}'
```

See [API.md](../API.md) for complete API documentation.

**Q: What recipe websites are supported?**

A: The service uses the `recipe-scrapers` library which supports 100+ popular
recipe websites. See `config/recipe_scraping/recipe_blog_urls.json` for a
curated list of popular sites.

**Q: How do I get nutritional information for a recipe?**

A: Use the `/api/v1/nutritional-info/analyze` endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/nutritional-info/analyze" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": "your-recipe-id"}'
```

### Common Errors

**Q: I'm getting a "Database connection failed" error. What should I do?**

A: Check the following:

1. Ensure PostgreSQL is running
2. Verify your `DATABASE_URL` in `.env` is correct
3. Check database credentials and permissions
4. Ensure the database exists

**Q: Recipe scraping is failing for certain websites. Why?**

A: Possible causes:

1. The website may have changed its HTML structure
2. The website may block scraping attempts
3. Rate limiting may be in effect
4. The website may not be supported by `recipe-scrapers`

Try scraping from a different source or open an issue with the specific URL.

**Q: I'm getting "API rate limit exceeded" errors. What should I do?**

A: The service implements rate limiting to prevent abuse:

1. Check your request frequency
2. Implement backoff and retry logic in your client
3. Consider caching responses
4. Contact us if you need higher rate limits

### Development

**Q: How do I run tests?**

A: Run tests using pytest:

```bash
# All tests with coverage
pytest --cov=app tests/

# Unit tests only
poetry run test-unit

# Specific test file
pytest tests/unit/test_recipe_service.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed testing guidelines.

**Q: How do I format and lint my code?**

A: Use the provided tools:

```bash
# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy app/

# Or run pre-commit hooks
pre-commit run --all-files
```

**Q: What Python version should I use?**

A: Python 3.13 is required (strict requirement per CLAUDE.md).

## Response Times

Please note these are approximate response times:

| Channel              | Expected Response Time |
|----------------------|------------------------|
| Security Advisories  | 48 hours               |
| GitHub Issues        | 3-5 business days      |
| GitHub Discussions   | 5-7 business days      |
| Pull Requests        | 3-5 business days      |

Response times may vary based on:

- Issue complexity
- Maintainer availability
- Number of open issues
- Community involvement

## Community Guidelines

When seeking support:

### Do

- ✅ Search existing issues and discussions before posting
- ✅ Provide detailed information and context
- ✅ Include relevant code samples, logs, and error messages
- ✅ Be respectful and patient
- ✅ Follow up with additional information if requested
- ✅ Close issues when resolved
- ✅ Thank contributors who help you

### Don't

- ❌ Create duplicate issues
- ❌ Post security vulnerabilities publicly
- ❌ Demand immediate responses
- ❌ Post off-topic content
- ❌ Include sensitive information (API keys, passwords, etc.)
- ❌ Bump issues excessively

### How to Ask Good Questions

1. **Be specific** - Clearly describe what you're trying to do
2. **Provide context** - Include relevant details about your environment
3. **Show your work** - Share what you've tried so far
4. **Include examples** - Code samples, error messages, logs
5. **Format properly** - Use code blocks and markdown
6. **One issue per topic** - Don't combine multiple questions

## Bug Report Best Practices

When reporting a bug, include:

1. **Clear description** - What is the bug?
2. **Steps to reproduce** - How can we replicate it?
3. **Expected behavior** - What should happen?
4. **Actual behavior** - What actually happens?
5. **Environment** - OS, Python version, deployment type
6. **Logs** - Relevant error messages (redact sensitive info)
7. **Code samples** - Minimal reproducible example

### Example Bug Report

```markdown
**Description**: Recipe scraping fails with ConnectionTimeout for all URLs

**Steps to Reproduce**:
1. Send POST request to `/api/v1/recipes/scrape`
2. With payload: `{"url": "https://example.com/recipe"}`
3. Observe timeout error

**Expected**: Recipe data returned within 30 seconds
**Actual**: ConnectionTimeout after 10 seconds

**Environment**:
- OS: Ubuntu 22.04
- Python: 3.13.1
- Deployment: Docker
- PostgreSQL: 15.2
- Redis: 7.0.10

**Logs**:

    ERROR: ConnectionTimeout: Request timed out after 10 seconds

**Additional Context**: This started happening after upgrading to version 1.2.0
```

## Additional Resources

### External Documentation

- **Python**: <https://docs.python.org/3/>
- **FastAPI**: <https://fastapi.tiangolo.com/>
- **SQLAlchemy**: <https://docs.sqlalchemy.org/>
- **Poetry**: <https://python-poetry.org/docs/>
- **pytest**: <https://docs.pytest.org/>
- **recipe-scrapers**: <https://github.com/hhursev/recipe-scrapers>

### Specifications

- **OpenAPI Spec**: Available at `/docs` endpoint (Swagger UI)
- **ReDoc**: Available at `/redoc` endpoint
- **OpenAPI JSON**: `openapi.yaml` in repository root

### Tools and Integrations

- **Postman Collection**: See `postman/` directory
- **Client Libraries**: See [API.md](../API.md) for examples
- **Docker Compose**: `docker-compose.yml` for local development

## Still Need Help?

If you can't find an answer:

1. **Search** the [documentation](../README.md) thoroughly
2. **Check** [existing issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues)
3. **Browse** [discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions)
4. **Ask** in [GitHub Discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions)
5. **Create** a new
   [issue](https://github.com/Recipe-Web-App/recipe-scraper-service/issues/new/choose)
   with all relevant details

---

Thank you for using the Recipe Scraper Service! We appreciate your
participation in our community.
