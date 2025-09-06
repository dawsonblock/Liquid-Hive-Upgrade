# Liquid Hive Developer Guide

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **Yarn 1.22+** - Package manager
- **Docker 24+** - Containerization
- **Docker Compose V2** - Multi-container orchestration
- **Git** - Version control

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd liquid-hive-upgrade

# Run initial setup
make setup

# Install all dependencies
make install

# Start development environment
make dev

# Verify everything is working
make check
```

## Development Environment

### Project Structure

```
liquid-hive-upgrade/
├── apps/                    # Backend applications
│   └── api/                # Main API service
├── frontend/               # React frontend
├── services/               # Microservices
│   ├── feedback_api/       # Feedback service
│   └── oracle_api/         # Oracle service
├── src/                    # Shared Python code
├── tests/                  # Test suites
├── scripts/                # Build and utility scripts
├── docs/                   # Documentation
├── infra/                  # Infrastructure configs
├── configs/                # Configuration files
└── Makefile               # Build system
```

### Development Commands

#### Essential Commands
```bash
# Check system status
make status

# Start development environment
make dev

# Stop development environment
make dev-stop

# View logs
make logs

# Run tests
make test

# Run linting
make lint

# Build project
make build
```

#### Advanced Commands
```bash
# Run CI pipeline locally
make ci

# Full CI with all checks
make ci-full

# Security scanning
make security-scan

# Performance testing
make performance-test

# Reset development environment
make dev-reset

# Update dependencies
make update-deps
```

### Frontend Development

#### Getting Started
```bash
cd frontend

# Install dependencies
yarn install

# Start development server
yarn dev

# Build for production
yarn build

# Run tests
yarn test

# Run linting
yarn lint
```

#### Available Scripts
- `yarn dev` - Start development server
- `yarn build` - Production build
- `yarn build:staging` - Staging build
- `yarn build:analyze` - Build with analysis
- `yarn test` - Run tests
- `yarn test:watch` - Watch mode tests
- `yarn test:coverage` - Coverage report
- `yarn lint` - Run linting
- `yarn lint:fix` - Fix linting issues
- `yarn type-check` - TypeScript checking
- `yarn format` - Format code
- `yarn clean` - Clean build artifacts

#### Development Features
- **Hot Module Replacement** - Instant updates
- **TypeScript Support** - Full type checking
- **Path Aliases** - Clean imports (`@/components`)
- **Code Splitting** - Automatic chunk optimization
- **Bundle Analysis** - `yarn analyze`
- **Pre-commit Hooks** - Automatic linting/formatting

### Backend Development

#### Getting Started
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run API server
cd apps/api
python main.py

# Run tests
python -m pytest tests/

# Run linting
ruff check .
```

#### API Development
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **SQLAlchemy** - Database ORM
- **Redis** - Caching and sessions
- **WebSocket** - Real-time communication

#### Service Architecture
- **API Gateway** - Main entry point
- **Feedback Service** - User feedback collection
- **Oracle Service** - AI/ML processing
- **Event Bus** - Inter-service communication

### Testing

#### Test Types
- **Unit Tests** - Individual component testing
- **Integration Tests** - Service integration testing
- **End-to-End Tests** - Full workflow testing
- **Performance Tests** - Load and stress testing

#### Running Tests
```bash
# Run all tests
make test

# Run Python tests only
make test-python

# Run frontend tests only
make test-frontend

# Run integration tests
make test-integration

# Run with coverage
make test-coverage
```

#### Test Configuration
- **Jest** - Frontend testing framework
- **Pytest** - Python testing framework
- **Testing Library** - React component testing
- **Coverage Reports** - HTML and JSON output

### Code Quality

#### Linting
```bash
# Run all linting
make lint

# Python linting
make lint-python

# Frontend linting
make lint-frontend

# Docker linting
make lint-docker
```

#### Code Formatting
```bash
# Format Python code
ruff format .

# Format frontend code
cd frontend && yarn format
```

#### Pre-commit Hooks
The project uses Husky and lint-staged for pre-commit hooks:
- Automatic code formatting
- Linting checks
- Type checking
- Test execution

### Docker Development

#### Development Containers
```bash
# Start all services
make dev

# Start specific service
docker compose up api

# View service logs
make logs-api

# Rebuild containers
docker compose up --build
```

#### Container Management
```bash
# Build all images
make docker-build

# Push to registry
make docker-push

# Clean up containers
docker compose down -v

# Remove unused images
docker system prune -f
```

### Configuration

#### Environment Variables
Create a `.env` file in the project root:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/liquid_hive
REDIS_URL=redis://localhost:6379

# Frontend Configuration
VITE_BACKEND_URL=http://localhost:8001
VITE_API_TIMEOUT=30000

# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# Monitoring
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
ALERT_EMAIL=alerts@company.com
```

#### Configuration Files
- `configs/base/settings.yaml` - Base configuration
- `configs/dev/settings.yaml` - Development overrides
- `configs/prod/settings.yaml` - Production overrides
- `frontend/.env.local` - Frontend environment

### Debugging

#### Frontend Debugging
```bash
# Start with debug mode
yarn dev --debug

# Run tests in debug mode
yarn test:debug

# Analyze bundle
yarn analyze
```

#### Backend Debugging
```bash
# Run with debug logging
DEBUG=1 python main.py

# Use debugger
python -m pdb main.py

# Profile performance
python -m cProfile main.py
```

#### Docker Debugging
```bash
# Run container interactively
docker run -it --rm liquid-hive-api bash

# Check container logs
docker logs <container-id>

# Inspect container
docker inspect <container-id>
```

### Performance Optimization

#### Build Optimization
```bash
# Run optimized build
python scripts/build_optimizer.py

# Clean build cache
python scripts/build_optimizer.py --clean-cache 7

# Monitor build performance
python scripts/build_monitor.py --watch
```

#### Frontend Optimization
- **Code Splitting** - Automatic chunk splitting
- **Tree Shaking** - Remove unused code
- **Minification** - Terser optimization
- **Compression** - Gzip/Brotli support
- **Caching** - Browser and CDN caching

#### Backend Optimization
- **Connection Pooling** - Database connections
- **Caching** - Redis caching layer
- **Async Processing** - Non-blocking operations
- **Load Balancing** - Multiple worker processes

### Monitoring and Observability

#### Health Checks
```bash
# Check system health
make check

# Check specific services
make check-services

# Check build status
make check-build
```

#### Metrics Collection
```bash
# Run monitoring
python scripts/build_monitor.py

# Continuous monitoring
python scripts/build_monitor.py --watch

# Generate report
python scripts/build_monitor.py --output report.json
```

#### Logging
- **Structured Logging** - JSON format
- **Log Levels** - DEBUG, INFO, WARN, ERROR
- **Log Aggregation** - Centralized logging
- **Log Rotation** - Automatic cleanup

### Security

#### Security Scanning
```bash
# Run security scans
make security-scan

# Check dependencies
safety check

# Scan for vulnerabilities
bandit -r src/
```

#### Security Best Practices
- **Input Validation** - Sanitize all inputs
- **Authentication** - JWT tokens
- **Authorization** - Role-based access
- **HTTPS** - Encrypted communication
- **Secrets Management** - Environment variables

### Deployment

#### Local Deployment
```bash
# Build for production
make build-all

# Deploy to staging
make deploy

# Deploy to production
make deploy-prod
```

#### Container Deployment
```bash
# Build images
make docker-build

# Push to registry
make docker-push

# Deploy with Helm
helm upgrade --install liquid-hive infra/helm/liquid-hive
```

### Troubleshooting

#### Common Issues

**Build Failures**
```bash
# Check system status
make status

# Clean and rebuild
make clean
make build-all

# Check dependencies
make check-deps
```

**Service Issues**
```bash
# Check service health
make check-services

# View service logs
make logs

# Restart services
make dev-stop
make dev
```

**Performance Issues**
```bash
# Check system metrics
make metrics

# Run performance tests
make performance-test

# Monitor resources
python scripts/build_monitor.py --watch
```

#### Debug Mode
```bash
# Enable debug logging
export DEBUG=1

# Verbose output
make build VERBOSE=1

# Debug frontend
cd frontend && yarn test:debug
```

### Contributing

#### Development Workflow
1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

#### Code Standards
- Follow existing code style
- Write comprehensive tests
- Update documentation
- Use meaningful commit messages
- Keep commits atomic

#### Pull Request Process
1. Ensure all tests pass
2. Run `make ci` locally
3. Update documentation if needed
4. Request review from maintainers
5. Address feedback promptly

### Resources

#### Documentation
- [Build System Guide](BUILD_SYSTEM.md)
- [API Documentation](api/overview.md)
- [Architecture Overview](architecture/system-overview.md)
- [Deployment Guide](DEPLOYMENT.md)

#### Tools and Services
- [Vite Documentation](https://vitejs.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Jest Documentation](https://jestjs.io/)

#### Support
- **Issues** - GitHub Issues
- **Discussions** - GitHub Discussions
- **Slack** - #liquid-hive-dev
- **Email** - dev@liquid-hive.dev

---

**Happy Coding!** 🚀

For questions or help, don't hesitate to reach out to the development team.
