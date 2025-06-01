# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  POETRY_VERSION=1.8.2 \
  POETRY_VIRTUALENVS_CREATE=false

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  libpq-dev \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy only the dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies via Poetry (no virtualenv)
RUN poetry install --no-root

# Copy the rest of the application
COPY . .

# Expose the app port
EXPOSE 8000

# Default command (adjust if needed)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
