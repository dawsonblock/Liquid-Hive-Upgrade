# Liquid Hive Upgrade

Advanced AI Agent Platform with memory management and vector search capabilities.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### Development Setup

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd liquid-hive-upgrade
   pip install -e .[dev]
   cd frontend && yarn install
   ```

2. **Run the application:**
   ```bash
   # Start all services
   docker compose up
   
   # Or run individually
   # Backend API
   uvicorn apps.api.main:app --reload --port 8000
   
   # Frontend
   cd frontend && yarn dev
   ```

3. **Access the application:**
   - API: http://localhost:8000
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs

### Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/
pytest tests/integration/

# Frontend tests
cd frontend && yarn test
```

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /healthz` - Kubernetes health check
- `GET /version` - Version information
- `POST /api/memory/ingest` - Ingest text into memory
- `POST /api/memory/query` - Query memory with semantic search
- `GET /api/memory/health` - Memory system health
- `GET /api/memory/stats` - Memory system statistics

### Docker Services

- **api**: FastAPI backend (port 8000)
- **frontend**: React frontend (port 3000)
- **redis**: Optional caching (port 6379)
- **qdrant**: Optional vector storage (port 6333)

### Development

```bash
# Install development dependencies
pip install -e .[dev]

# Run linting
ruff check .
black --check .

# Run type checking
mypy src

# Run tests with coverage
pytest --cov=src --cov-report=html
```

## Architecture

- **Backend**: FastAPI with async support
- **Frontend**: React with TypeScript and Vite
- **Memory**: In-memory storage with vector search simulation
- **Deployment**: Docker containers with health checks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
