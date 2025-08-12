# Deployment Guide

This guide covers deployment strategies for the Recipe Scraper Service across different environments and platforms.

## Table of Contents

-   [Prerequisites](#prerequisites)
-   [Environment Configuration](#environment-configuration)
-   [Local Development](#local-development)
-   [Docker Deployment](#docker-deployment)
-   [Kubernetes Deployment](#kubernetes-deployment)
-   [Production Considerations](#production-considerations)
-   [Monitoring and Logging](#monitoring-and-logging)
-   [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

-   **CPU**: Minimum 2 cores, recommended 4+ cores for production
-   **Memory**: Minimum 2GB RAM, recommended 4GB+ for production
-   **Storage**: Minimum 10GB available space
-   **Network**: Outbound HTTPS access for external API calls

### Software Dependencies

-   **Python**: 3.13+ (with JIT compiler support)
-   **Poetry**: 2.1.3+ for dependency management
-   **Docker**: 24.0+ and Docker Compose 2.0+
-   **PostgreSQL**: 14+ (can be containerized)
-   **Redis**: 6.2+ (can be containerized)

## Environment Configuration

### Environment Variables

Create environment-specific configuration files:

#### Development (.env.development)

```bash
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=recipe_scraper_dev
POSTGRES_SCHEMA=public
RECIPE_SCRAPER_DB_USER=recipe_user_dev
RECIPE_SCRAPER_DB_PASSWORD=dev_password

# Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300

# External APIs
SPOONACULAR_API_KEY=your_dev_api_key
SPOONACULAR_RATE_LIMIT=150

# Security
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
ENABLE_RATE_LIMITING=false
SECRET_KEY=dev_secret_key_change_in_production

# Performance
ENABLE_CACHING=true
CACHE_LAYERS=["memory", "redis"]
```

#### Production (.env.production)

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
POSTGRES_HOST=prod-postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=recipe_scraper_prod
POSTGRES_SCHEMA=public
RECIPE_SCRAPER_DB_USER=recipe_user_prod
RECIPE_SCRAPER_DB_PASSWORD=${POSTGRES_PASSWORD}

# Cache
REDIS_URL=redis://prod-redis.example.com:6379/0
CACHE_TTL=3600

# External APIs
SPOONACULAR_API_KEY=${SPOONACULAR_API_KEY}
SPOONACULAR_RATE_LIMIT=100

# Security
ALLOWED_ORIGINS=["https://yourdomain.com"]
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=100
SECRET_KEY=${SECRET_KEY}

# Performance
ENABLE_CACHING=true
CACHE_LAYERS=["memory", "redis", "file"]
WORKERS=4
MAX_CONNECTIONS=20
```

### Configuration Management

#### Using Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
    name: recipe-scraper-secrets
type: Opaque
stringData:
    POSTGRES_PASSWORD: "secure_db_password" # pragma: allowlist secret
    SPOONACULAR_API_KEY: "your_spoonacular_key" # pragma: allowlist secret
    SECRET_KEY: "your_secret_key" # pragma: allowlist secret
```

#### Using Docker Secrets

```bash
# Create secrets
echo "secure_db_password" | docker secret create postgres_password -
echo "your_spoonacular_key" | docker secret create spoonacular_key -

# Reference in docker-compose.yml
secrets:
  - postgres_password
  - spoonacular_key
```

## Local Development

### Poetry Setup

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Start development server
poetry run dev

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose Setup

```bash
# Start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f recipe-scraper-service

# Stop services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v
```

## Docker Deployment

### Single Container Deployment

#### Build Production Image

```bash
# Build optimized production image
docker build -t recipe-scraper-service:latest .

# Build with specific version tag
docker build -t recipe-scraper-service:v1.0.0 .
```

#### Run Container

```bash
# Run with environment file
docker run -d \
  --name recipe-scraper \
  --env-file .env.production \
  -p 8000:8000 \
  --restart unless-stopped \
  recipe-scraper-service:latest

# Run with individual environment variables
docker run -d \
  --name recipe-scraper \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e POSTGRES_HOST=your-db-host \
  -e REDIS_URL=redis://your-redis-host:6379/0 \
  --restart unless-stopped \
  recipe-scraper-service:latest
```

### Multi-Service Docker Compose

#### Production docker-compose.yml

```yaml
version: "3.8"

services:
    recipe-scraper:
        image: recipe-scraper-service:latest
        build:
            context: .
            dockerfile: Dockerfile
        ports:
            - "8000:8000"
        environment:
            - ENVIRONMENT=production
            - POSTGRES_HOST=postgres
            - REDIS_URL=redis://redis:6379/0
        env_file:
            - .env.production
        depends_on:
            - postgres
            - redis
        restart: unless-stopped
        healthcheck:
            test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
            interval: 30s
            timeout: 10s
            retries: 3
            start_period: 60s

    postgres:
        image: postgres:15-alpine
        environment:
            POSTGRES_DB: recipe_scraper_prod
            POSTGRES_USER: recipe_user_prod
            POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
        volumes:
            - postgres_data:/var/lib/postgresql/data
        ports:
            - "5432:5432"
        restart: unless-stopped

    redis:
        image: redis:7-alpine
        command: redis-server --appendonly yes
        volumes:
            - redis_data:/data
        ports:
            - "6379:6379"
        restart: unless-stopped

    nginx:
        image: nginx:alpine
        ports:
            - "80:80"
            - "443:443"
        volumes:
            - ./nginx.conf:/etc/nginx/nginx.conf:ro
            - ./ssl:/etc/nginx/ssl:ro
        depends_on:
            - recipe-scraper
        restart: unless-stopped

volumes:
    postgres_data:
    redis_data:
```

## Kubernetes Deployment

### Namespace Setup

```yaml
apiVersion: v1
kind: Namespace
metadata:
    name: recipe-scraper
    labels:
        name: recipe-scraper
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
    name: recipe-scraper-config
    namespace: recipe-scraper
data:
    ENVIRONMENT: "production"
    LOG_LEVEL: "INFO"
    POSTGRES_HOST: "postgres-service"
    POSTGRES_PORT: "5432"
    POSTGRES_DB: "recipe_scraper_prod"
    REDIS_URL: "redis://redis-service:6379/0"
    ENABLE_RATE_LIMITING: "true"
    RATE_LIMIT_PER_MINUTE: "100"
```

### Secret Management

```yaml
apiVersion: v1
kind: Secret
metadata:
    name: recipe-scraper-secrets
    namespace: recipe-scraper
type: Opaque
stringData:
    POSTGRES_PASSWORD: "secure_db_password" # pragma: allowlist secret
    SPOONACULAR_API_KEY: "your_spoonacular_key" # pragma: allowlist secret
    SECRET_KEY: "your_secret_key" # pragma: allowlist secret
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: recipe-scraper-deployment
    namespace: recipe-scraper
    labels:
        app: recipe-scraper
spec:
    replicas: 3
    selector:
        matchLabels:
            app: recipe-scraper
    template:
        metadata:
            labels:
                app: recipe-scraper
        spec:
            containers:
                - name: recipe-scraper
                  image: recipe-scraper-service:v1.0.0
                  ports:
                      - containerPort: 8000
                  envFrom:
                      - configMapRef:
                            name: recipe-scraper-config
                      - secretRef:
                            name: recipe-scraper-secrets
                  resources:
                      requests:
                          memory: "512Mi"
                          cpu: "250m"
                      limits:
                          memory: "1Gi"
                          cpu: "500m"
                  livenessProbe:
                      httpGet:
                          path: /api/v1/liveness
                          port: 8000
                      initialDelaySeconds: 30
                      periodSeconds: 30
                      timeoutSeconds: 10
                  readinessProbe:
                      httpGet:
                          path: /api/v1/readiness
                          port: 8000
                      initialDelaySeconds: 15
                      periodSeconds: 15
                      timeoutSeconds: 5
                  env:
                      - name: POSTGRES_PASSWORD
                        valueFrom:
                            secretKeyRef:
                                name: recipe-scraper-secrets
                                key: POSTGRES_PASSWORD
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
    name: recipe-scraper-service
    namespace: recipe-scraper
spec:
    selector:
        app: recipe-scraper
    ports:
        - protocol: TCP
          port: 8000
          targetPort: 8000
    type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
    name: recipe-scraper-ingress
    namespace: recipe-scraper
    annotations:
        kubernetes.io/ingress.class: nginx
        cert-manager.io/cluster-issuer: letsencrypt-prod
        nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
    tls:
        - hosts:
              - api.yourdomain.com
          secretName: recipe-scraper-tls
    rules:
        - host: api.yourdomain.com
          http:
              paths:
                  - path: /
                    pathType: Prefix
                    backend:
                        service:
                            name: recipe-scraper-service
                            port:
                                number: 8000
```

### High Availability

The deployment includes a PodDisruptionBudget to ensure service availability during cluster maintenance operations. This guarantees that at least one pod remains available during voluntary disruptions like node drains or cluster upgrades.

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
    name: recipe-scraper-hpa
    namespace: recipe-scraper
spec:
    scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: recipe-scraper-deployment
    minReplicas: 2
    maxReplicas: 10
    metrics:
        - type: Resource
          resource:
              name: cpu
              target:
                  type: Utilization
                  averageUtilization: 70
        - type: Resource
          resource:
              name: memory
              target:
                  type: Utilization
                  averageUtilization: 80
```

### Security Best Practices

The deployment follows Kubernetes security best practices and passes kube-score validation:

#### Container Security
- Runs as non-privileged user with high UID/GID to avoid host conflicts
- Uses read-only root filesystem for enhanced security
- Drops all Linux capabilities by default
- Enforces resource limits to prevent resource exhaustion

#### Network Security
- Network policies restrict ingress and egress traffic to essential services only
- Pod anti-affinity rules distribute pods across nodes for resilience
- Separate health check endpoints for liveness and readiness probes

#### Availability
- Multiple replicas with pod disruption budgets ensure service continuity
- Health checks enable automatic recovery from failures
- Resource requests guarantee minimum compute allocation

## Production Considerations

### Performance Optimization

#### Application Settings

```bash
# Increase worker processes
WORKERS=4
WORKER_CLASS=uvicorn.workers.UvicornWorker

# Connection pooling
MAX_CONNECTIONS=20
POOL_SIZE=10
MAX_OVERFLOW=20

# Caching configuration
CACHE_TTL=3600
CACHE_MAX_SIZE=1000
ENABLE_COMPRESSION=true
```

#### Database Optimization

```sql
-- Create indexes for frequently queried columns
CREATE INDEX CONCURRENTLY idx_recipes_created_at ON recipes(created_at);
CREATE INDEX CONCURRENTLY idx_recipes_difficulty ON recipes(difficulty_level);
CREATE INDEX CONCURRENTLY idx_ingredients_name ON ingredients(name);

-- Analyze tables for query optimization
ANALYZE recipes;
ANALYZE ingredients;
ANALYZE nutritional_info;
```

#### Redis Configuration

```redis
# /etc/redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec
```

### Security Hardening

#### Container Security

```dockerfile
# Use non-root user
USER 1001:1001

# Remove package managers
RUN apt-get remove -y apt-get && \
    rm -rf /var/lib/apt/lists/*

# Set secure file permissions
COPY --chown=1001:1001 --chmod=644 app/ ./app/
```

#### Network Security

```yaml
# Network policies for Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
    name: recipe-scraper-netpol
spec:
    podSelector:
        matchLabels:
            app: recipe-scraper
    policyTypes:
        - Ingress
        - Egress
    ingress:
        - from:
              - namespaceSelector:
                    matchLabels:
                        name: ingress-nginx
          ports:
              - protocol: TCP
                port: 8000
    egress:
        - to: []
          ports:
              - protocol: TCP
                port: 443 # HTTPS
              - protocol: TCP
                port: 5432 # PostgreSQL
              - protocol: TCP
                port: 6379 # Redis
```

### Backup and Recovery

#### Database Backup

```bash
#!/bin/bash
# backup-script.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="recipe_scraper_prod"

# Create backup
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $DB_NAME \
  | gzip > $BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql.gz

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql.gz \
  s3://your-backup-bucket/database/

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

#### Automated Backup CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
    name: postgres-backup
    namespace: recipe-scraper
spec:
    schedule: "0 2 * * *" # Daily at 2 AM
    jobTemplate:
        spec:
            template:
                spec:
                    containers:
                        - name: postgres-backup
                          image: postgres:15-alpine
                          command:
                              - /bin/bash
                              - -c
                              - |
                                  pg_dump -h postgres-service -U $POSTGRES_USER $POSTGRES_DB \
                                    | gzip > /backup/backup_$(date +%Y%m%d_%H%M%S).sql.gz
                          env:
                              - name: POSTGRES_USER
                                value: "recipe_user_prod"
                              - name: POSTGRES_DB
                                value: "recipe_scraper_prod"
                              - name: PGPASSWORD
                                valueFrom:
                                    secretKeyRef:
                                        name: recipe-scraper-secrets
                                        key: POSTGRES_PASSWORD
                          volumeMounts:
                              - name: backup-storage
                                mountPath: /backup
                    volumes:
                        - name: backup-storage
                          persistentVolumeClaim:
                              claimName: backup-pvc
                    restartPolicy: OnFailure
```

## Monitoring and Logging

### Prometheus Monitoring

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
    name: recipe-scraper-metrics
    namespace: recipe-scraper
spec:
    selector:
        matchLabels:
            app: recipe-scraper
    endpoints:
        - port: http
          path: /metrics
          interval: 30s
```

### Grafana Dashboard

```json
{
    "dashboard": {
        "title": "Recipe Scraper Service",
        "panels": [
            {
                "title": "Request Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": "rate(http_requests_total[5m])",
                        "legendFormat": "Requests/sec"
                    }
                ]
            },
            {
                "title": "Response Time",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "95th percentile"
                    }
                ]
            }
        ]
    }
}
```

### Centralized Logging

```yaml
apiVersion: logging.coreos.com/v1
kind: ClusterLogForwarder
metadata:
    name: recipe-scraper-logs
    namespace: openshift-logging
spec:
    outputs:
        - name: elasticsearch-output
          type: elasticsearch
          url: https://elasticsearch.example.com:9200
    pipelines:
        - name: recipe-scraper-pipeline
          inputRefs:
              - application
          filterRefs:
              - recipe-scraper-filter
          outputRefs:
              - elasticsearch-output
```

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check container logs
docker logs recipe-scraper

# Check resource usage
docker stats recipe-scraper

# Verify environment variables
docker exec recipe-scraper env | grep -E "(POSTGRES|REDIS)"
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it postgres-pod -- psql -U recipe_user_prod -d recipe_scraper_prod -c "SELECT 1;"

# Check service DNS resolution
kubectl exec -it recipe-scraper-pod -- nslookup postgres-service
```

#### High Memory Usage

```bash
# Check memory usage
kubectl top pods -n recipe-scraper

# Analyze memory patterns
kubectl exec -it recipe-scraper-pod -- cat /proc/meminfo
```

### Health Check Endpoints

Use the built-in health endpoints for troubleshooting:

```bash
# Basic health check
curl http://localhost:8000/api/v1/health

# Liveness probe
curl http://localhost:8000/api/v1/liveness

# Readiness probe
curl http://localhost:8000/api/v1/readiness
```

### Performance Tuning

#### Database Tuning

```sql
-- Check slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Analyze table statistics
SELECT schemaname, tablename, n_live_tup, n_dead_tup
FROM pg_stat_user_tables
WHERE schemaname = 'public';
```

#### Cache Optimization

```bash
# Check Redis memory usage
redis-cli info memory

# Monitor cache hit ratios
redis-cli info stats | grep keyspace
```

For additional support and troubleshooting, refer to the [API documentation](API.md) and [contributing guidelines](CONTRIBUTING.md).
