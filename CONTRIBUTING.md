# Contributing to Recipe Scraper Service

We love your input! We want to make contributing to Recipe Scraper Service as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Request Process

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

### Prerequisites

- Python 3.13+
- Poetry 2.1.3+
- Docker & Docker Compose
- Git with pre-commit hooks

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/jsamuelsen/recipe-scraper-service.git
cd recipe-scraper-service

# Install dependencies
poetry install
poetry shell

# Set up pre-commit hooks
pre-commit install

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Start development server
poetry run dev
```

## Code Style and Standards

### Code Formatting
- **Black**: Code formatting with 88 character line length
- **isort**: Import sorting with Black profile
- **Ruff**: Comprehensive linting with auto-fix capabilities

### Type Checking
- **MyPy**: Strict type checking is required
- All functions must have type hints
- Return types must be explicitly declared

### Documentation
- **Google-style docstrings** are required for all public functions and classes
- **pydoclint** validation ensures documentation completeness
- API endpoints must include comprehensive OpenAPI documentation

### Security
- **Bandit** security analysis for Python code
- **Safety** dependency vulnerability scanning
- **detect-secrets** prevents secrets from being committed
- All security issues must be addressed before merging

## Testing Requirements

### Test Coverage
- Minimum 80% test coverage required (target 95%)
- Coverage below 80% will fail the build
- All new features must include comprehensive tests

### Test Organization
```
tests/
├── unit/          # Fast, isolated tests with mocked dependencies
├── integration/   # End-to-end API tests with real databases
└── performance/   # Load testing and benchmarks
```

### Test Naming Convention
- Use `*_test.py` pattern (not `test_*.py`)
- Test files should mirror the application structure
- Test functions should be descriptive: `test_create_recipe_with_valid_url_returns_201`

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=app tests/

# Run only unit tests (fast)
poetry run test-unit

# Run integration tests
pytest tests/integration/ -v

# Run performance benchmarks
pytest tests/performance/ --benchmark-only

# Generate HTML coverage report
pytest --cov=app --cov-report=html tests/
```

## Quality Assurance

### Pre-commit Hooks
All code must pass pre-commit hooks before submission:

```bash
# Run all checks
pre-commit run --all-files

# Individual checks
black .
isort .
ruff check . --fix
mypy app/
bandit app/
safety check
```

### Code Complexity
- **Radon** complexity analysis must maintain grade B or higher
- Functions with complexity grade C or lower require refactoring
- Maintainability index must remain above threshold

## Commit Message Format

**⚠️ IMPORTANT**: We strictly follow [Conventional Commits](https://www.conventionalcommits.org/) for automated changelog generation and semantic versioning.

### Required Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types (Required)

| Type | Description | Changelog | Version Bump |
|------|-------------|-----------|--------------|
| `feat` | ✨ A new feature | ✅ Yes | Minor |
| `fix` | 🐛 A bug fix | ✅ Yes | Patch |
| `security` | 🔒 Security improvement/fix | ✅ Yes | Patch |
| `perf` | 🚀 Performance improvement | ✅ Yes | Patch |
| `refactor` | 📦 Code refactoring | ✅ Yes | Patch |
| `revert` | 🗑 Revert previous commit | ✅ Yes | Patch |
| `docs` | 📚 Documentation changes | ❌ No | None |
| `style` | 💎 Code style changes | ❌ No | None |
| `test` | 🧪 Test changes | ❌ No | None |
| `build` | 🛠 Build system changes | ❌ No | None |
| `ci` | ⚙️ CI configuration changes | ❌ No | None |
| `chore` | ♻️ Other maintenance tasks | ❌ No | None |

### Scopes (Optional)
- `api` - API endpoints and routing
- `scraper` - Recipe scraping functionality
- `cache` - Caching system
- `db` - Database models and queries
- `auth` - Authentication and authorization
- `config` - Configuration management
- `docker` - Docker and containerization
- `k8s` - Kubernetes manifests
- `deps` - Dependency updates
- `release` - Release-related changes

### Breaking Changes
For breaking changes, add `BREAKING CHANGE:` in the footer or use `!` after type:
```
feat!: redesign API response format

BREAKING CHANGE: All API responses now use the new standardized format
```

### Examples
```
feat(api): add ingredient substitution endpoint
fix(cache): resolve Redis connection timeout issue
security(auth): implement rate limiting for login endpoint
perf(scraper): optimize recipe parsing performance
docs(api): update endpoint documentation
test(scraper): add integration tests for recipe creation
chore(deps): update FastAPI to v0.118.0
```

### Validation
- Commit messages are validated by pre-commit hooks
- Invalid commits will be rejected
- Use `git commit --amend` to fix commit messages if needed

### Automation Benefits
- **Automatic Changelog**: Conventional commits generate changelog entries
- **Semantic Versioning**: Version bumps based on commit types
- **GitHub Releases**: Automated release creation with proper notes

## Feature Development Guidelines

### API Design
- Follow RESTful principles
- Use consistent response formats
- Implement proper HTTP status codes
- Include comprehensive request/response validation
- Provide clear error messages with structured format

### Database Changes
- All schema changes must include migrations
- Database models should follow domain-driven design
- Use proper indexes for query optimization
- Test migrations both up and down

### External Integrations
- All external API calls must be properly mocked in tests
- Implement proper error handling and retries
- Use dependency injection for testability
- Include rate limiting considerations

### Security Considerations
- Never commit secrets or credentials
- Use environment variables for configuration
- Implement proper input validation
- Follow security best practices for API design
- Include security testing for new endpoints

## Documentation Requirements

### Code Documentation
- All public functions and classes must have Google-style docstrings
- Include parameter types and descriptions
- Document return values and exceptions
- Provide usage examples for complex functions

### API Documentation
- All endpoints must include OpenAPI documentation
- Provide example requests and responses
- Document all possible error responses
- Include parameter validation details

### Architecture Documentation
- Update CLAUDE.md when adding new patterns or frameworks
- Document significant architectural decisions
- Include deployment and configuration changes
- Update README.md for user-facing changes

## Issue Reporting

When reporting issues, please include:

1. **Bug Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the behavior
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, OS, Docker version, etc.
6. **Logs**: Relevant log output (redact sensitive information)

### Bug Report Template

```markdown
**Bug Description**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
A clear and concise description of what you expected to happen.

**Screenshots/Logs**
If applicable, add screenshots or log output to help explain your problem.

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Python Version: [e.g. 3.13.1]
- Poetry Version: [e.g. 2.1.3]
- Docker Version: [e.g. 24.0.5]

**Additional Context**
Add any other context about the problem here.
```

## Feature Request Process

1. **Search Existing Issues**: Check if the feature has already been requested
2. **Create Feature Request**: Use the feature request template
3. **Discuss Design**: Engage in discussion about implementation approach
4. **Create Implementation Plan**: Break down the feature into manageable tasks
5. **Submit Pull Request**: Follow the PR process outlined above

## Performance Guidelines

### Optimization Targets
- Health checks: < 10ms response time
- Recipe scraping: < 2s for most websites
- API throughput: 1000+ requests/second (with caching)
- Memory usage: < 512MB under normal load

### Performance Testing
- All performance-critical code must include benchmarks
- Use pytest-benchmark for performance testing
- Monitor performance impact in CI/CD pipeline
- Include load testing for new endpoints

## Monitoring and Observability

### Metrics
- All new endpoints must include Prometheus metrics
- Business logic should include relevant custom metrics
- Monitor cache performance and hit ratios
- Track error rates and response times

### Logging
- Use structured logging with proper log levels
- Include request IDs for traceability
- Log important business events
- Avoid logging sensitive information

## Release Process

1. **Version Bump**: Update version in `pyproject.toml`
2. **Update Changelog**: Document all changes in `CHANGELOG.md`
3. **Test Suite**: Ensure all tests pass
4. **Security Scan**: Run full security analysis
5. **Performance Test**: Verify performance benchmarks
6. **Documentation**: Update relevant documentation
7. **Tag Release**: Create Git tag with version number
8. **Deploy**: Follow deployment procedures

## Code of Conduct

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Unacceptable Behavior

Examples of unacceptable behavior include:

- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

## Questions?

Don't hesitate to ask questions! You can:

- Open an issue with the `question` label
- Reach out to maintainers directly
- Check existing documentation and issues first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- Project README.md
- Release notes
- GitHub contributors page

Thank you for contributing to Recipe Scraper Service! 🍽️
