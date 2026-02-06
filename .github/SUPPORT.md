# Support

Thank you for using the Recipe Scraper Service! This document provides resources to help you get support.

## Documentation

Before asking for help, please check our documentation:

### Primary Documentation

- **[README.md](../README.md)** - Complete feature overview, setup instructions, and API documentation
- **[CLAUDE.md](../CLAUDE.md)** - Development commands, architecture overview, and developer guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and development workflow
- **[SECURITY.md](SECURITY.md)** - Security features, best practices, and vulnerability reporting

### Code Examples

- **[`.env.example`](../.env.example)** - Configuration examples
- **[Docker Compose](../docker-compose.yml)** - Deployment examples
- **[Kubernetes Manifests](../k8s/)** - K8s deployment configurations

## Getting Help

### 1. Search Existing Resources

Before creating a new issue, please search:

- [Existing Issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues) - Someone may have already asked
- [Closed Issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues?q=is%3Aissue+is%3Aclosed) - Your question
  may already be answered
- [Discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions) - Community Q&A

### 2. GitHub Discussions (Recommended for Questions)

For general questions, use [GitHub Discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions):

**When to use Discussions:**

- "How do I...?" questions
- Configuration help
- Best practice advice
- Integration questions
- Architecture discussions
- Troubleshooting (non-bug)

**Categories:**

- **Q&A** - Ask questions and get answers
- **Ideas** - Share feature ideas and proposals
- **Show and Tell** - Share your implementations
- **General** - Everything else

### 3. GitHub Issues (For Bugs and Features)

Use [GitHub Issues](https://github.com/Recipe-Web-App/recipe-scraper-service/issues/new/choose) for:

- Bug reports
- Feature requests
- Performance issues
- Documentation problems
- Security vulnerabilities (low severity - use Security Advisories for critical)

**Issue Templates:**

- **Bug Report** - Report unexpected behavior
- **Feature Request** - Suggest new functionality
- **Performance Issue** - Report performance problems
- **Documentation** - Documentation improvements
- **Security Vulnerability** - Low-severity security issues

### 4. Security Issues

**IMPORTANT:** For security vulnerabilities, use:

- [GitHub Security Advisories](https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new) (private)
- See [SECURITY.md](SECURITY.md) for details

**Never report security issues publicly through issues or discussions.**

## Common Questions

### Setup and Configuration

**Q: How do I get started?**
A: See the Quick Start section in [README.md](../README.md#quick-start)

**Q: What environment variables are required?**
A: Check [`.env.example`](../.env.example) for all configuration options

**Q: How do I enable TLS/HTTPS?**
A: Configure your reverse proxy (nginx, traefik) to handle TLS termination

### API Usage

**Q: What endpoints are available?**
A: See the API documentation at `/docs` (Swagger UI) or `/redoc` when running the service

**Q: How do I authenticate?**
A: Use JWT tokens obtained from the authentication endpoints. See [README.md](../README.md#authentication)

**Q: What rate limits apply?**
A: Default rate limits are configured per-IP. See [README.md](../README.md#rate-limiting)

### Troubleshooting

**Q: Service fails to start?**

- Check logs: `docker logs <container-name>`
- Verify environment variables
- Check Redis connectivity
- Review [README.md](../README.md#troubleshooting) troubleshooting section

**Q: Redis connection errors?**

- Verify Redis is running: `redis-cli ping`
- Check REDIS_URL environment variable
- Ensure network connectivity

**Q: Performance issues?**

- Check Redis cache hit rates
- Review rate limiting configuration
- Monitor with Prometheus metrics at `/metrics`
- See [Performance Issue Template](.github/ISSUE_TEMPLATE/performance_issue.yml)

**Q: CORS errors?**

- Configure `CORS_ALLOWED_ORIGINS` environment variable
- Check request Origin header
- Review middleware configuration

### Development

**Q: How do I contribute?**
A: See [CONTRIBUTING.md](CONTRIBUTING.md) for complete guidelines

**Q: How do I run tests?**
A: Run `uv run pytest` or see [CLAUDE.md](../CLAUDE.md#testing) for test commands

**Q: What's the code structure?**
A: See Architecture Overview in [CLAUDE.md](../CLAUDE.md#architecture-overview)

## Response Times

We aim to:

- Acknowledge issues/discussions within 48 hours
- Respond to questions within 1 week
- Fix critical bugs as priority
- Review PRs within 1-2 weeks

Note: This is a community project. Response times may vary.

## Commercial Support

This is an open-source project. Commercial support is not currently available.

## Community Guidelines

When asking for help:

- **Be specific** - Include exact error messages, versions, configurations
- **Provide context** - What were you trying to do? What happened instead?
- **Include details** - Environment, deployment method, relevant logs
- **Be patient** - Maintainers and community volunteers help in their free time
- **Be respectful** - Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- **Search first** - Check if your question was already answered
- **Give back** - Help others when you can

## Bug Report Best Practices

When reporting bugs, include:

- Python version
- Deployment environment (Docker/K8s/Local)
- Exact error messages
- Steps to reproduce
- Expected vs actual behavior
- Relevant configuration (redact secrets!)
- Logs (redact sensitive info!)

Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.yml) - it helps ensure you provide all needed information.

## Additional Resources

### Python Resources

- [Python Documentation](https://docs.python.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Related Projects

- [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) - Python library for scraping recipes
- [FastAPI](https://github.com/tiangolo/fastapi) - Modern Python web framework

## Still Need Help?

If you can't find an answer:

1. Check [Discussions](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions)
2. Ask a new question in [Q&A](https://github.com/Recipe-Web-App/recipe-scraper-service/discussions/new?category=q-a)
3. For bugs, create an [Issue](https://github.com/Recipe-Web-App/recipe-scraper-service/issues/new/choose)

We're here to help!
