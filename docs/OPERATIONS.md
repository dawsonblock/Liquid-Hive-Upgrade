# Operations Guide

This guide covers deployment, scaling, monitoring, and maintenance of Liquid Hive in production environments.

## Environment Variables

### Required Variables

```bash
# Application
APP_ENV=production
SECRET_KEY=your-secret-key-here
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://host:port/db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=1
```

### Optional Variables

```bash
# Monitoring
METRICS_ENABLED=true
PROMETHEUS_PORT=9090
HEALTH_CHECK_INTERVAL=10

# Features
RAG_ENABLED=true
AGENT_AUTONOMY=true
SWARM_PROTOCOL=true
SAFETY_CHECKS=true
CONFIDENCE_MODELING=true

# Logging
LOG_LEVEL=WARNING
LOG_FORMAT=json
```

## Deployment

### Docker Compose (Single Server)

```bash
# Production deployment
export APP_ENV=production
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -hex 16)

# Start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose ps
curl http://localhost:8000/health
```

### Kubernetes

```bash
# Apply Helm chart
helm install liquid-hive ./infra/helm/liquid-hive \
  --set app.environment=production \
  --set app.secretKey=$(openssl rand -hex 32) \
  --set database.password=$(openssl rand -hex 16)

# Check deployment
kubectl get pods
kubectl get services
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml liquid-hive

# Check services
docker service ls
docker stack ps liquid-hive
```

## Scaling

### Horizontal Scaling

#### API Scaling

```bash
# Scale API replicas
docker-compose up -d --scale api=3

# Or with Kubernetes
kubectl scale deployment liquid-hive-api --replicas=3
```

#### Database Scaling

```bash
# Read replicas
docker-compose -f docker-compose.yml -f docker-compose.read-replicas.yml up -d

# Connection pooling
export DATABASE_POOL_SIZE=20
export DATABASE_MAX_OVERFLOW=30
```

#### Redis Scaling

```bash
# Redis Cluster
docker-compose -f docker-compose.yml -f docker-compose.redis-cluster.yml up -d

# Redis Sentinel
docker-compose -f docker-compose.yml -f docker-compose.redis-sentinel.yml up -d
```

### Vertical Scaling

```yaml
# docker-compose.override.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Dashboard health
curl http://localhost:3000/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping
```

### Metrics

#### Prometheus Metrics

- API request metrics: `http_requests_total`
- Database connection metrics: `db_connections_active`
- Redis metrics: `redis_commands_total`
- Custom business metrics: `liquid_hive_*`

#### Grafana Dashboards

Access Grafana at http://localhost:3001 (admin/admin)

Key dashboards:
- API Performance
- Database Performance
- Redis Performance
- System Resources
- Error Rates

### Logging

#### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about application flow
- `WARNING`: Something unexpected happened
- `ERROR`: An error occurred but the application can continue
- `CRITICAL`: A serious error occurred

#### Log Aggregation

```bash
# ELK Stack
docker-compose -f docker-compose.yml -f docker-compose.elk.yml up -d

# Fluentd
docker-compose -f docker-compose.yml -f docker-compose.fluentd.yml up -d
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U liquid_hive liquid_hive > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose exec -T postgres psql -U liquid_hive liquid_hive < backup_20240101_120000.sql
```

### Redis Backup

```bash
# Create backup
docker-compose exec redis redis-cli BGSAVE
docker cp liquid-hive-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# Restore backup
docker cp ./redis_backup_20240101_120000.rdb liquid-hive-redis:/data/dump.rdb
docker-compose restart redis
```

### Configuration Backup

```bash
# Backup configuration
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz configs/

# Backup secrets
kubectl get secret liquid-hive-secrets -o yaml > secrets_backup.yaml
```

## Security

### SSL/TLS

```bash
# Generate certificates
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Update nginx configuration
# Add SSL configuration to infra/docker/nginx.conf
```

### Secrets Management

```bash
# Using Kubernetes secrets
kubectl create secret generic liquid-hive-secrets \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=postgres-password=$(openssl rand -hex 16)

# Using Docker secrets
echo "your-secret-key" | docker secret create liquid-hive-secret-key -
```

### Network Security

```yaml
# docker-compose.security.yml
services:
  api:
    networks:
      - internal
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.tls=true"
  
  postgres:
    networks:
      - internal
    # No external ports exposed
```

## Maintenance

### Updates

```bash
# Update application
git pull origin main
docker-compose build
docker-compose up -d

# Update dependencies
pip install -r requirements.txt --upgrade
yarn upgrade

# Database migrations
alembic upgrade head
```

### Cleanup

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune
```

### Performance Tuning

#### Database Tuning

```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

#### Redis Tuning

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check for memory leaks
   - Increase container memory limits
   - Optimize database queries

2. **Slow Response Times**
   - Check database performance
   - Review Redis cache hit rates
   - Monitor network latency

3. **Database Connection Issues**
   - Verify connection string
   - Check firewall rules
   - Review connection pool settings

4. **Redis Connection Issues**
   - Verify Redis is running
   - Check network connectivity
   - Review Redis configuration

### Debugging

```bash
# View logs
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis

# Debug container
docker-compose exec api bash
docker-compose exec postgres psql -U liquid_hive liquid_hive

# Check resource usage
docker stats
kubectl top pods
```

## Disaster Recovery

### Recovery Procedures

1. **Database Corruption**
   - Restore from latest backup
   - Run database integrity checks
   - Verify data consistency

2. **Service Outage**
   - Check service health
   - Review logs for errors
   - Restart affected services
   - Scale up if needed

3. **Data Loss**
   - Stop all writes
   - Restore from backup
   - Verify data integrity
   - Resume operations

### RTO/RPO Targets

- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 1 hour
- **Backup Frequency**: Every 6 hours
- **Retention Period**: 30 days