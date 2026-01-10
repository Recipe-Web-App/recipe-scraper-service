# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version  | Supported          |
| -------- | ------------------ |
| latest   | :white_check_mark: |
| < latest | :x:                |

We recommend always running the latest version for security patches.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

### Private Reporting (Preferred)

Report security vulnerabilities using [GitHub Security Advisories](https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new).

This allows us to:

- Discuss the vulnerability privately
- Develop and test a fix
- Coordinate disclosure timing
- Issue a CVE if necessary

### What to Include

When reporting a vulnerability, please include:

1. **Description** - Clear description of the vulnerability
2. **Impact** - What can an attacker achieve?
3. **Reproduction Steps** - Step-by-step instructions to reproduce
4. **Affected Components** - Which parts of the service are affected
5. **Suggested Fix** - If you have ideas for remediation
6. **Environment** - Version, configuration, deployment details
7. **Proof of Concept** - Code or requests demonstrating the issue (if safe to share)

### Example Report

```text
Title: JWT Token Signature Bypass

Description: The JWT validation does not properly verify signatures...

Impact: An attacker can forge tokens and gain unauthorized access...

Steps to Reproduce:
1. Create a JWT with algorithm "none"
2. Send to /api/v1/recipes/scrape
3. Token is accepted without signature verification

Affected: src/app/core/security/jwt.py line 45

Suggested Fix: Enforce algorithm whitelist and reject "none"

Environment: v1.2.3, Docker deployment
```

## Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Varies by severity (critical: days, high: weeks, medium: months)

## Severity Levels

### Critical

- Remote code execution
- Authentication bypass
- Privilege escalation to admin
- Mass data exposure

### High

- Token forgery/manipulation
- Injection vulnerabilities
- Unauthorized access to user data
- Denial of service affecting all users

### Medium

- Information disclosure (limited)
- CSRF vulnerabilities
- Rate limiting bypass
- Session fixation

### Low

- Verbose error messages
- Security header issues
- Best practice violations

## Security Features

This service implements multiple security layers:

### Authentication Security

- **JWT Tokens** - Cryptographically signed tokens with configurable expiration
- **OAuth2 Support** - Standard OAuth2 flows with PKCE support
- **Token Validation** - Strict signature and claims verification
- **Role-Based Access Control** - Granular permissions system

### Application Security

- **Rate Limiting** - Per-IP and per-user request throttling
- **CORS Protection** - Configurable cross-origin policies
- **Input Validation** - Pydantic models validate all inputs
- **URL Validation** - Strict URL validation before scraping
- **Secure Headers** - CSP, HSTS, X-Frame-Options, etc.

### Infrastructure

- **Secret Management** - Secrets via environment variables (never in code)
- **Audit Logging** - Comprehensive security event logging
- **Health Monitoring** - Liveness/readiness probes
- **TLS Support** - HTTPS with configurable certificates
- **Non-root Container** - Application runs as non-privileged user

## Security Best Practices

### For Operators

1. **Use TLS/HTTPS** - Always encrypt traffic in production
2. **Rotate Secrets** - Regularly rotate JWT signing keys
3. **Monitor Logs** - Watch for suspicious patterns
4. **Update Dependencies** - Keep Python packages current
5. **Limit Exposure** - Use network policies and firewalls
6. **Configure CORS** - Whitelist only trusted origins
7. **Set Rate Limits** - Protect against brute force and DoS
8. **Redis Security** - Use authentication and TLS
9. **Backup Secrets** - Securely store signing key backups

### For Developers

1. **Never Commit Secrets** - Use `.env` (gitignored)
2. **Validate Inputs** - Use Pydantic for all inputs
3. **Handle Errors Securely** - Don't leak sensitive info in errors
4. **Run Security Checks** - Use `bandit` before committing
5. **Review Dependencies** - Check for known vulnerabilities
6. **Test Security** - Include security test cases

## Security Checklist

Before deploying:

- [ ] TLS/HTTPS configured
- [ ] Strong JWT signing key (256+ bits)
- [ ] Rate limiting configured
- [ ] CORS whitelist configured
- [ ] Secrets in environment variables (not code)
- [ ] Redis authentication enabled
- [ ] Security headers enabled
- [ ] Audit logging enabled
- [ ] Dependencies updated
- [ ] Security scan passed (bandit)
- [ ] Network policies applied
- [ ] Monitoring and alerting configured

## Known Security Considerations

### Token Storage

- Access tokens are short-lived JWTs (recommended: 15 minutes)
- Refresh tokens stored in Redis with TTL
- Revoked tokens maintained in blacklist

### Redis Security

- Optional authentication (recommended)
- Optional TLS (recommended in production)
- TTL on all cached data

### URL Scraping

- URLs are validated before scraping
- External requests have timeouts
- Response size limits enforced
- Content-Type verification

## Disclosure Policy

We follow **coordinated disclosure**:

1. Vulnerability reported privately
2. We confirm and develop fix
3. Fix tested and released
4. Public disclosure after fix is deployed
5. Credit given to reporter (if desired)

## Security Updates

Subscribe to:

- [GitHub Security Advisories](https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories)
- [Release Notes](https://github.com/Recipe-Web-App/recipe-scraper-service/releases)
- Watch repository for security patches

## Contact

For security concerns: Use [GitHub Security Advisories](https://github.com/Recipe-Web-App/recipe-scraper-service/security/advisories/new)

For general questions: See [SUPPORT.md](SUPPORT.md)

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged (with
permission) in:

- Security advisories
- Release notes
- This document

Thank you for helping keep this project secure!
