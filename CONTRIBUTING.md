# Contributing to Liquid Hive

Welcome to Liquid Hive! We're excited to have you contribute to our advanced AI agent platform.

## 🚀 Quick Start

1. **Fork & Clone**
   ```bash
   git clone https://github.com/your-username/liquid-hive.git
   cd liquid-hive
   ```

2. **Development Setup**
   ```bash
   make dev-setup  # Install dependencies and setup
   make dev        # Start development environment
   ```

3. **Make Changes**
   - Create a feature branch: `git checkout -b feature/your-feature`
   - Make your changes
   - Run tests: `make test`
   - Check linting: `make lint`

4. **Submit PR**
   - Push your branch
   - Create a Pull Request with clear description
   - Ensure all CI checks pass

## 🏗️ Development Workflow

### Prerequisites
- Python 3.11+ 
- Node.js 18+
- Yarn package manager
- Docker & Docker Compose

### Architecture
```
liquid-hive/
├── src/                    # Core libraries (canonical source)
├── apps/api/              # FastAPI application
├── frontend/              # React frontend  
├── tests/                 # Test suites
├── infra/                 # Infrastructure & deployment
└── docs/                  # Documentation
```

### Available Commands
```bash
make dev        # Start development stack
make test       # Run all tests
make lint       # Run linters
make format     # Format code
make security   # Security checks
make ci         # Full CI pipeline locally
```

## 🧪 Testing

### Test Structure
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests  
- `tests/performance/` - Performance tests with k6

### Running Tests
```bash
# All tests
make test

# Specific test types
make test-unit
make test-integration 
make test-performance
```

### Coverage Requirements
- Minimum 80% code coverage
- All new features must include tests
- Integration tests for API endpoints

## 📝 Code Standards

### Python
- Use `ruff` for linting and formatting
- Follow PEP 8 guidelines
- Type hints required for all functions
- Docstrings for all public functions

### TypeScript/React
- Use `eslint` and `prettier`
- Follow React best practices
- Functional components with hooks
- Proper TypeScript typing

### Imports
- Library imports: `from src.<module> import ...`
- Relative imports within modules: `from .local_module import ...`
- Never import from `apps/api/` - use `src/` instead

## 🔒 Security

- No secrets in code or commits
- Use environment variables for configuration
- Follow OWASP security guidelines
- Security scanning with bandit and safety

## 🚢 Deployment

### Environments
- **Development**: Local docker-compose stack
- **Production**: Kubernetes with Helm

### Release Process
1. Update version in `src/version.py`
2. Update `CHANGELOG.md`
3. Create release PR
4. Tag release: `git tag v1.x.x`
5. GitHub Actions handles deployment

## 📚 Documentation

- Update relevant docs with changes
- API changes require OpenAPI updates
- Architectural decisions go in `docs/adrs/`

## 🐛 Bug Reports

Use GitHub Issues with:
- Clear reproduction steps
- Environment details
- Expected vs actual behavior
- Relevant logs/screenshots

## 💡 Feature Requests

- Check existing issues first
- Provide clear use case
- Consider breaking changes
- Discuss in issues before large features

## 🤝 Code Review

- All changes require PR review
- CI must pass (tests, linting, security)
- Reviewers check code quality, security, tests
- Maintain backward compatibility when possible

## 📞 Getting Help

- GitHub Issues for bugs/features
- Discussions for questions
- Check documentation first

Thank you for contributing to Liquid Hive! 🎉