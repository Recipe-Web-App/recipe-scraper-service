# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please DO NOT report security vulnerabilities through public GitHub issues.**

### For Critical and High Severity Issues

If you discover a security vulnerability, please report it via **GitHub Security Advisories**:

1. Go to https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new
2. Click "Report a vulnerability"
3. Fill out the security advisory form with details

### What to Include in Your Report

To help us better understand and resolve the issue, please include as much of the following information as possible:

- **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass, etc.)
- **Full path** of the source file(s) related to the vulnerability
- **Location** of the affected code (tag/branch/commit or direct URL)
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact** of the vulnerability
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - **Critical**: 1-3 days
  - **High**: 7-14 days
  - **Medium**: 14-30 days
  - **Low**: 30-90 days

## Severity Levels

### Critical

- Remote code execution
- Authentication bypass
- Privilege escalation
- Data exposure of sensitive information (API keys, credentials, PII)

### High

- SQL injection
- Cross-site scripting (XSS) with significant impact
- Server-side request forgery (SSRF)
- Insecure deserialization
- Path traversal

### Medium

- Cross-site request forgery (CSRF)
- Information disclosure (non-sensitive)
- Denial of service (DoS)
- Insecure direct object references

### Low

- Security misconfiguration
- Missing security headers
- Verbose error messages
- Minor information leakage

## Security Features

The Recipe Scraper Service implements several security features:

### Authentication & Authorization

- API key authentication for external access
- Rate limiting on all endpoints
- Request validation and sanitization
- Session management with secure token handling

### Data Protection

- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **XSS Prevention**: Input validation and output encoding
- **CSRF Protection**: CSRF tokens for state-changing operations
- **Secrets Management**: Environment variables for sensitive configuration
- **TLS/SSL**: HTTPS enforcement in production

### Infrastructure Security

- **Database**: PostgreSQL with connection pooling and prepared statements
- **Caching**: Redis with secure connection strings
- **Docker**: Multi-stage builds, non-root user, minimal base images
- **Logging**: Security event logging without exposing sensitive data

### Dependency Security

- **Automated Scanning**: Dependabot for vulnerability detection
- **Security Audits**: Regular `safety` and `bandit` scans
- **SBOM Generation**: Software Bill of Materials for releases

## Security Best Practices for Operators

### Deployment Security Checklist

Before deploying to production, ensure:

- [ ] All environment variables are set and secrets are secured
- [ ] Database uses strong passwords and restricted access
- [ ] Redis is password-protected and not exposed publicly
- [ ] API keys are rotated regularly
- [ ] TLS/SSL certificates are valid and up to date
- [ ] Security headers are configured (HSTS, CSP, X-Frame-Options, etc.)
- [ ] Rate limiting is enabled and configured appropriately
- [ ] Logging is enabled but doesn't capture sensitive data
- [ ] Firewall rules restrict access to necessary ports only
- [ ] Container images are scanned for vulnerabilities
- [ ] Dependencies are up to date

### Configuration Security

**Environment Variables** (store in `.env`, never commit):

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname # pragma: allowlist secret

# API Keys
SPOONACULAR_API_KEY=your_api_key_here

# Redis
REDIS_URL=redis://:password@localhost:6379

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here
```

**Secure Defaults**:

- Use environment-specific configurations
- Enable HTTPS redirect in production
- Set secure cookie flags (Secure, HttpOnly, SameSite)
- Configure CORS to allow only trusted domains

### Monitoring & Incident Response

- Monitor logs for suspicious activity
- Set up alerts for failed authentication attempts
- Track API rate limit violations
- Review security scan results regularly
- Have an incident response plan

## Known Security Considerations

### Recipe Scraping

- **URL Validation**: All URLs are validated before scraping to prevent SSRF
- **Content Sanitization**: Scraped content is sanitized to prevent XSS
- **Rate Limiting**: Per-source rate limiting to prevent abuse
- **Timeout Controls**: Requests have timeout limits to prevent DoS

### Third-Party Integrations

- **Spoonacular API**: API keys are stored securely and rotated
- **External Recipe Sites**: Scraping respects robots.txt and rate limits
- **Image Downloads**: Images are validated and scanned for malicious content

### Database Security

- **Connection Pooling**: Limited connections to prevent resource exhaustion
- **Query Parameterization**: All queries use SQLAlchemy ORM or parameters
- **Access Control**: Least privilege principle for database users
- **Backup Encryption**: Database backups are encrypted at rest

## Disclosure Policy

### Coordinated Disclosure

We follow a coordinated disclosure process:

1. **Report Received**: We acknowledge your report within 48 hours
2. **Investigation**: We investigate and verify the vulnerability
3. **Fix Development**: We develop and test a fix
4. **Fix Deployment**: We deploy the fix to production
5. **Public Disclosure**: We publicly disclose the vulnerability after:
   - Fix is deployed to all affected systems
   - Affected users are notified (if applicable)
   - 90 days have passed (whichever comes first)

### Credit and Recognition

We appreciate the work of security researchers:

- We will credit you in the security advisory (unless you prefer to remain anonymous)
- Your name will be added to our [Security Hall of Fame](../README.md#security-hall-of-fame) (if you wish)
- We may offer a thank-you letter or swag for significant discoveries

## Security Updates

### How to Stay Informed

- **GitHub Security Advisories**: Subscribe to security advisories for this repository
- **Release Notes**: Check [CHANGELOG.md](../CHANGELOG.md) for security fixes
- **GitHub Watch**: Watch this repository for security-related releases
- **RSS Feed**: Subscribe to the releases RSS feed

### Applying Security Updates

```bash
# Update to the latest version
git pull origin main
poetry update
poetry install

# Review changelog for breaking changes
cat CHANGELOG.md

# Run tests
pytest

# Deploy to production
# (follow your deployment process)
```

## Security Tools

This project uses the following security tools:

### Automated Scanning

- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **Trivy**: Container and filesystem vulnerability scanner
- **CodeQL**: Semantic code analysis
- **Dependabot**: Automated dependency updates

### Running Security Scans Locally

```bash
# Python security scanner
poetry run bandit -r app/

# Dependency vulnerability check
poetry run safety check

# Pre-commit hooks (includes security checks)
pre-commit run --all-files
```

## Contact

For security concerns that don't require immediate disclosure:

- **Email**: security@recipe-web-app.com (if available)
- **GitHub**: @jsamuelsen

For urgent security issues, always use **GitHub Security Advisories**.

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)

## Acknowledgments

We thank the following security researchers for responsibly disclosing vulnerabilities:

<!-- List will be populated as researchers report vulnerabilities -->

_No vulnerabilities have been publicly disclosed at this time._

---

**Last Updated**: 2025-10-07

Thank you for helping keep the Recipe Scraper Service and our users safe!
