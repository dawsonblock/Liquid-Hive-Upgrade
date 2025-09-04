# Liquid-Hive-Upgrade Documentation

Welcome to the comprehensive documentation for Liquid-Hive-Upgrade, a robust Oracle Provider Router with Planner and Arena services.

## 📚 Documentation Structure

### 🏗️ [Architecture](architecture/)

System architecture, design decisions, and technical overview

- [System Overview](architecture/system-overview.md)
- [Component Architecture](architecture/components.md)
- [Data Flow](architecture/data-flow.md)
- [Security Architecture](architecture/security.md)
- [Deployment Architecture](architecture/deployment.md)

### 📖 [Runbooks](runbooks/)

Operational procedures and troubleshooting guides

- [Deployment Guide](runbooks/deployment.md)
- [Monitoring and Alerts](runbooks/monitoring.md)
- [Troubleshooting](runbooks/troubleshooting.md)
- [Database Operations](runbooks/database-ops.md)
- [Backup and Recovery](runbooks/backup-recovery.md)

### 🤔 [Architecture Decision Records (ADRs)](adrs/)

Historical record of architectural decisions

- [ADR-001: Technology Stack Selection](adrs/001-technology-stack.md)
- [ADR-002: Oracle Provider Interface](adrs/002-oracle-provider-interface.md)
- [ADR-003: Authentication Strategy](adrs/003-authentication-strategy.md)
- [ADR-004: Database Selection](adrs/004-database-selection.md)

### 🔌 [API Documentation](api/)

API specifications and integration guides

- [OpenAPI Specification](api/openapi.json)
- [Authentication](api/authentication.md)
- [Endpoints](api/endpoints.md)
- [SDKs](api/sdks.md)

### 🚀 [Deployment](deployment/)

Deployment guides and configuration

- [Docker Deployment](deployment/docker.md)
- [Kubernetes Deployment](deployment/kubernetes.md)
- [Cloud Deployment](deployment/cloud.md)
- [Environment Configuration](deployment/environment.md)

### 💻 [Development](development/)

Development guides and standards

- [Getting Started](development/getting-started.md)
- [Code Standards](development/code-standards.md)
- [Testing Guide](development/testing.md)
- [Contributing](../CONTRIBUTING.md)

## 🚀 Quick Start

1. **System Requirements**

   - Python 3.10+
   - Node.js 18+
   - Docker & Docker Compose
   - Kubernetes (for production)

2. **Local Development**

   ```bash
   # Clone repository
   git clone https://github.com/liquid-hive/upgrade.git
   cd liquid-hive-upgrade

   # Set up development environment
   make install
   make env-create
   make up-dev

   # Verify installation
   make health
   ```

3. **Production Deployment**

   ```bash
   # Docker Compose
   docker compose up -d

   # Kubernetes with Helm
   helm install liquid-hive-upgrade helm/
   ```

## 🏗️ System Overview

Liquid-Hive-Upgrade is a comprehensive system consisting of:

### Core Components

- **Unified Runtime**: FastAPI-based server with advanced routing
- **Oracle Providers**: Swappable LLM provider interface
- **Planner**: DAG-based task execution engine
- **Arena**: Model evaluation and comparison service

### Supporting Services

- **MongoDB**: Primary data storage
- **Redis**: Caching and session management
- **Neo4j**: Graph database for complex relationships
- **Qdrant**: Vector database for embeddings

### Observability Stack

- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **OpenTelemetry**: Distributed tracing
- **Alertmanager**: Alert routing and management

## 📊 Key Features

### 🔄 Hot-Swappable Providers

- Runtime provider switching without code changes
- Configurable routing profiles (cheap, balanced, quality)
- Circuit breaker patterns for reliability
- Economic routing with cost optimization

### 🧠 Intelligent Planning

- DAG-based task execution
- Parallel processing capabilities
- Retry mechanisms and error handling
- Built-in task operations

### 🏆 Model Arena

- A/B testing for model comparison
- Elo rating system
- Performance analytics
- Win-rate tracking

### 🔒 Enterprise Security

- JWT/API key authentication
- Role-based access control
- Rate limiting and quotas
- Audit logging with HMAC signatures

### 📈 Production Ready

- Auto-scaling with HPA
- Health checks and monitoring
- Comprehensive observability
- CI/CD pipelines

## 🛠️ Development Workflow

```bash
# Code quality checks
make lint              # Run linting
make security          # Security analysis
make complexity        # Code complexity analysis

# Testing
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only

# Build and deployment
make build             # Build application
make docker-build      # Build Docker image
make helm-install      # Deploy to Kubernetes
```

## 📈 Monitoring and Observability

### Metrics Available

- API request rates and latency
- Provider call success/failure rates
- Circuit breaker states
- Arena evaluation metrics
- Resource utilization

### Dashboards

- [API Metrics](../grafana/dashboards/api_metrics.json)
- [Training Metrics](../grafana/dashboards/training_metrics.json)
- [Infrastructure Metrics](../grafana/dashboards/infra_metrics.json)

### Alerts Configured

- High error rates (>5%)
- High latency (>2s p95)
- Circuit breaker trips
- Low Arena win rates
- Resource exhaustion

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details on:

- Development setup
- Code standards
- Testing requirements
- Submission process

## 📞 Support

- **Documentation**: This documentation
- **Issues**: [GitHub Issues](https://github.com/liquid-hive/upgrade/issues)
- **Security**: security@liquid-hive.dev
- **General**: support@liquid-hive.dev

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

**Last Updated**: $(date)
**Version**: 2.0.0
