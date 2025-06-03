"""App package initializer.

This package contains the core application components, including API routes,
configuration, database integration, middleware, models, schemas, services, and
utilities.
"""

import logging

from app.core.logging import configure_logging
from app.middleware.logging_middleware import InterceptHandler

# Configure logging for the entire app
configure_logging()

# Intercept all standard logging (including Uvicorn) and route to Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).handlers = [InterceptHandler()]
