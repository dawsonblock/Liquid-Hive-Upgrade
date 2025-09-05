# Getting Started with Liquid Hive

Welcome to Liquid Hive, an advanced AI agent platform. This guide will help you get up and running in 5 minutes.

## Prerequisites

- Python 3.10+ 
- Node.js 18+
- Docker and Docker Compose
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/liquid-hive.git
cd liquid-hive
```

### 2. Start with Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

This will start:
- API server on http://localhost:8000
- Dashboard on http://localhost:3000
- PostgreSQL database
- Redis cache
- Prometheus monitoring on http://localhost:9090
- Grafana dashboards on http://localhost:3001

### 3. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check dashboard
open http://localhost:3000
```

## Development Setup

### Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .[dev]

# Run tests
pytest

# Start API in development mode
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
# Navigate to dashboard
cd apps/dashboard

# Install dependencies
yarn install

# Start development server
yarn dev

# Run tests
yarn test
```

## Configuration

Configuration is managed through environment-specific YAML files:

- `configs/base/settings.yaml` - Base configuration
- `configs/dev/settings.yaml` - Development overrides
- `configs/prod/settings.yaml` - Production overrides

Set the `APP_ENV` environment variable to switch between environments:

```bash
export APP_ENV=development  # or staging, production, test
```

## Project Structure

```
liquid-hive/
├── apps/                    # Runnable applications
│   ├── api/                # FastAPI backend
│   └── dashboard/          # React frontend
├── libs/                   # Shared libraries
│   ├── core/              # Core functionality
│   ├── shared/            # Shared utilities
│   └── utils/             # Common utilities
├── configs/               # Configuration files
│   ├── base/             # Base configuration
│   ├── dev/              # Development overrides
│   └── prod/             # Production overrides
├── tests/                # Test suites
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── docs/                 # Documentation
├── infra/                # Infrastructure
│   ├── docker/           # Dockerfiles
│   ├── helm/             # Kubernetes manifests
│   └── gh-actions/       # CI/CD workflows
└── scripts/              # Utility scripts
```

## Common Commands

### Development

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Format code
black libs apps
isort libs apps
ruff format libs apps

# Type checking
mypy libs apps

# Linting
ruff check libs apps
```

### Docker

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f dashboard

# Stop services
docker-compose down
```

### Database

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change ports in `docker-compose.yml` or stop conflicting services
2. **Permission errors**: Ensure Docker has proper permissions
3. **Database connection**: Check PostgreSQL is running and accessible
4. **Redis connection**: Verify Redis is running on the correct port

### Getting Help

- Check the [Operations Guide](OPERATIONS.md) for deployment and scaling
- Review [Architecture Documentation](ARCHITECTURE.md) for system design
- Open an issue on GitHub for bugs or feature requests

## Next Steps

- Explore the [API Documentation](http://localhost:8000/docs) when running locally
- Check out the [Configuration Guide](CONFIGURATION.md) for advanced setup
- Read the [Contributing Guide](../CONTRIBUTING.md) to start contributing