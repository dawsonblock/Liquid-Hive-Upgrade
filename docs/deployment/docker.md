# Docker Deployment Guide

This guide covers deploying Liquid-Hive-Upgrade using Docker and Docker Compose for development and production environments.

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Minimum 4GB RAM
- Minimum 2 CPU cores

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/liquid-hive/upgrade.git
cd liquid-hive-upgrade
```

### 2. Environment Configuration

```bash
# Create environment file
cp .env.example .env

# Edit configuration (required)
nano .env
```

### 3. Start Services

```bash
# Start all services in development mode
docker compose --profile dev up -d

# Or start core services only
docker compose up -d
```

### 4. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/api/health

# View logs
docker compose logs -f api
```

## Environment Configuration

### Required Environment Variables

```bash
# Core Settings
ENVIRONMENT=production
ENABLE_PLANNER=true
ENABLE_ARENA=true

# Database URLs
MONGO_URL=mongodb://mongodb:27017/liquid_hive
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# API Keys (set in vault or environment)
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Security
ADMIN_TOKEN=your_secure_admin_token
JWT_ALGORITHM=RS256
API_JWT_AUDIENCE=liquid-hive

# Observability
OTEL_SERVICE_NAME=liquid-hive-upgrade
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
PROMETHEUS_ENABLED=true
```

### Optional Configuration

```bash
# Performance Tuning
WORKERS=4
MAX_TENANTS=1000
RATE_LIMIT_RPS=50

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Features
ENABLE_INTERNET_AGENT=false
TENANCY_MODE=multi
```

## Service Profiles

Docker Compose supports multiple profiles for different deployment scenarios:

### Default Profile (Core Services)

- API server
- MongoDB
- Redis
- Neo4j
- Qdrant
- Prometheus
- Grafana
- Alertmanager

```bash
docker compose up -d
```

### Development Profile

Includes development tools:

- All core services
- Adminer (database admin)
- Redis Commander

```bash
docker compose --profile dev up -d
```

### GPU Profile

For LLM serving with GPU support:

- Includes vLLM service with GPU acceleration

```bash
docker compose --profile gpu up -d
```

### Full Profile

All services including RAG document processing:

```bash
docker compose --profile full up -d
```

## Production Deployment

### 1. Production Environment File

Create a production-specific environment file:

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false

# Use secure passwords
NEO4J_PASSWORD=${NEO4J_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
ADMIN_TOKEN=${ADMIN_TOKEN}

# Production database URLs
MONGO_URL=mongodb://mongodb:27017/liquid_hive_prod
REDIS_URL=redis://redis:6379/0

# External observability endpoints
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.your-domain.com:4317
PROMETHEUS_ENABLED=true

# Performance settings
WORKERS=8
RATE_LIMIT_RPS=100
MAX_TENANTS=10000

# Security hardening
CORS_ORIGINS=["https://your-domain.com"]
RATE_LIMIT_BURST=200
```

### 2. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"
services:
  api:
    image: ghcr.io/liquid-hive/liquid-hive-upgrade:latest
    env_file: .env.production
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "0.5"
          memory: 1G
    healthcheck:
      test: ["CMD", "/usr/local/bin/health-check.sh"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - production-net

  mongodb:
    image: mongo:7.0
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_ROOT_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD}
    volumes:
      - mongodb_data:/data/db
      - ./scripts/mongo-init.js:/docker-entrypoint-initdb.d/init.js:ro
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
    networks:
      - production-net

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf:ro
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
    networks:
      - production-net

networks:
  production-net:
    driver: bridge

volumes:
  mongodb_data:
  redis_data:
```

### 3. Deploy Production

```bash
# Deploy production stack
docker compose -f docker-compose.prod.yml up -d

# Monitor deployment
docker compose -f docker-compose.prod.yml logs -f

# Check health
curl https://your-domain.com/api/health
```

## Container Security

### Security Best Practices

1. **Non-root User**: All containers run as non-root user (UID 10001)
2. **Read-only Filesystem**: Where possible, containers use read-only filesystems
3. **Resource Limits**: CPU and memory limits configured
4. **Health Checks**: Comprehensive health monitoring
5. **Network Isolation**: Services communicate via internal networks

### Security Configuration

```yaml
# Security context example
services:
  api:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp:rw,size=1G
      - /app/logs:rw,size=500M
```

## Monitoring and Observability

### Available Dashboards

Access monitoring dashboards:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### Key Metrics

Monitor these critical metrics:

- API response times and error rates
- Database connection pool status
- Cache hit rates
- Provider call success rates
- Resource utilization (CPU, memory)

### Custom Dashboards

Import pre-built dashboards:

```bash
# Copy dashboard configurations
cp grafana/dashboards/*.json /var/lib/grafana/dashboards/

# Restart Grafana
docker compose restart grafana
```

## Backup and Recovery

### Database Backups

```bash
# MongoDB backup
docker compose exec mongodb mongodump --out /backup

# Redis backup
docker compose exec redis redis-cli BGSAVE

# Copy backups to host
docker cp container_id:/backup ./backups/
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/$DATE"

mkdir -p $BACKUP_DIR

# Backup MongoDB
docker compose exec -T mongodb mongodump --quiet --out /tmp/backup
docker cp $(docker compose ps -q mongodb):/tmp/backup $BACKUP_DIR/mongodb

# Backup Redis
docker compose exec -T redis redis-cli --rdb /tmp/dump.rdb
docker cp $(docker compose ps -q redis):/tmp/dump.rdb $BACKUP_DIR/redis.rdb

# Compress backup
tar -czf "backup_$DATE.tar.gz" -C ./backups $DATE

echo "Backup completed: backup_$DATE.tar.gz"
```

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check service status
docker compose ps

# View logs
docker compose logs api

# Check resource usage
docker stats

# Verify network connectivity
docker compose exec api ping mongodb
```

#### Database Connection Issues

```bash
# Test MongoDB connection
docker compose exec api python -c "
import pymongo
client = pymongo.MongoClient('mongodb://mongodb:27017/')
print('Connected:', client.admin.command('ping'))
"

# Test Redis connection
docker compose exec api python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print('Redis ping:', r.ping())
"
```

#### Performance Issues

```bash
# Check resource usage
docker compose exec api top

# Monitor API performance
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/health"

# View slow queries
docker compose logs mongodb | grep "slow operation"
```

### Log Collection

```bash
# Collect all logs
docker compose logs --no-color > system_logs_$(date +%Y%m%d).log

# Follow specific service logs
docker compose logs -f api

# Export metrics
curl http://localhost:9090/api/v1/query?query=up > metrics_status.json
```

## Scaling and Performance

### Horizontal Scaling

```yaml
# Scale API service
services:
  api:
    deploy:
      replicas: 5

  # Add load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
```

### Vertical Scaling

```yaml
# Increase resource limits
services:
  api:
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 8G
        reservations:
          cpus: "1.0"
          memory: 2G
```

### Performance Tuning

```bash
# Optimize Docker daemon
echo '{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5
}' > /etc/docker/daemon.json

systemctl restart docker
```

## Development Workflow

### Local Development

```bash
# Start development environment
make up-dev

# View logs
make logs

# Run tests against containers
make test-integration

# Stop services
make down
```

### Hot Reloading

For development, mount source code for hot reloading:

```yaml
services:
  api:
    volumes:
      - ./src:/app/src:ro
      - ./config:/app/config:ro
    environment:
      - RELOAD=true
```

### Debugging

```bash
# Access container shell
docker compose exec api bash

# Debug with Python
docker compose exec api python -c "
import sys
sys.path.append('/app/src')
from unified_runtime.server import app
print('App loaded successfully')
"
```

## Cleanup

### Remove All Services

```bash
# Stop and remove containers
docker compose down

# Remove volumes (WARNING: This deletes data)
docker compose down -v

# Remove images
docker compose down --rmi all

# Full cleanup
docker system prune -a --volumes
```

### Selective Cleanup

```bash
# Remove only stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune
```

---

This guide provides comprehensive Docker deployment instructions. For Kubernetes deployment, see the [Kubernetes Deployment Guide](kubernetes.md).
