# Pull Request

## Description

<!-- Provide a clear and concise description of the changes in this PR -->

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Performance improvement
- [ ] Refactoring (no functional changes)
- [ ] Documentation update
- [ ] Security fix
- [ ] Dependency update
- [ ] Configuration change
- [ ] Other (please describe):

## Related Issues

<!-- Link to related issues using keywords: Fixes #123, Resolves #456, Related to #789 -->

Fixes #

## Changes Made

<!-- List the specific changes made in this PR -->

-
-
-

## Security Impact

<!-- Does this change affect security, authentication, or data protection? -->

- [ ] This PR affects authentication/authorization
- [ ] This PR affects data validation or sanitization
- [ ] This PR affects API rate limiting
- [ ] This PR affects sensitive data handling
- [ ] This PR has security implications
- [ ] No security impact

<!-- If checked, please describe the security implications -->

## Breaking Changes

<!-- List any breaking changes and migration steps -->

- [ ] This PR introduces breaking changes

<!-- If checked, describe the breaking changes and how users should migrate -->

## Testing

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All existing tests pass

### Test Details

<!-- Describe the testing you performed -->

**Manual Testing:**

- <!-- Add manual testing details -->

**Automated Tests:**

- <!-- Add automated test details -->

**Test Coverage:**

- Current coverage:
- Coverage change:
- Meets 80% minimum requirement: [ ] Yes [ ] No

## Configuration Changes

<!-- Are there new environment variables or configuration options? -->

- [ ] New environment variables added
- [ ] Configuration defaults changed
- [ ] No configuration changes

<!-- If checked, list the new/changed configuration -->

**New Configuration:**

```bash
# Add environment variables here
```

## Database/Storage Changes

<!-- Does this affect the database schema or Redis usage? -->

- [ ] Database schema changes (migration required)
- [ ] Database indexes added/modified
- [ ] Redis data structure changes
- [ ] No database/storage changes

<!-- If checked, describe the migration path -->

## Performance Impact

<!-- Has performance been tested? Are there any impacts? -->

- [ ] Performance tested
- [ ] No performance impact expected
- [ ] Performance improvement (provide metrics)
- [ ] Potential performance degradation (explained below)

<!-- If there's a performance impact, provide details -->

## Deployment Notes

<!-- Any special deployment considerations? -->

- [ ] Requires database migration
- [ ] Requires configuration changes
- [ ] Requires service restart
- [ ] Requires dependency updates
- [ ] Safe to deploy with rolling update
- [ ] Standard deployment

<!-- Provide deployment instructions if needed -->

## Documentation

<!-- Has documentation been updated? -->

- [ ] README.md updated
- [ ] CLAUDE.md updated
- [ ] API.md updated (API documentation)
- [ ] Code comments added/updated
- [ ] OpenAPI spec updated
- [ ] No documentation needed

## Checklist

<!-- Ensure all items are completed before requesting review -->

- [ ] Code follows the project's style guidelines (`poetry run black .`, `poetry run isort .`)
- [ ] Linting passes (`poetry run ruff check .`)
- [ ] Type checking passes (`poetry run mypy app/`)
- [ ] Self-review of code performed
- [ ] Code commented, particularly in hard-to-understand areas
- [ ] No new security vulnerabilities introduced (`poetry run bandit app/`)
- [ ] All tests pass locally (`pytest --cov=app tests/`)
- [ ] Test coverage meets 80% minimum requirement
- [ ] No sensitive information (secrets, keys, tokens) committed
- [ ] Commit messages follow conventional commit format
- [ ] Branch is up to date with target branch
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)

## Python-Specific Checks

- [ ] Code formatted with Black (88 char line length)
- [ ] Imports sorted with isort
- [ ] Type hints added for new functions
- [ ] Docstrings follow Google style guide
- [ ] No new pydoclint violations

## Screenshots/Logs (if applicable)

<!-- Add screenshots, logs, or other visual aids -->

## Additional Context

<!-- Add any additional context, concerns, or notes for reviewers -->

## Reviewer Notes

<!-- Specific areas where you'd like reviewer focus -->

Please pay special attention to:

- <!-- Add areas of focus -->
- <!-- Add areas of focus -->

---

**For Reviewers:**

- [ ] Code review completed
- [ ] Security implications reviewed
- [ ] Test coverage is adequate
- [ ] Documentation is clear and complete
- [ ] Performance implications considered
