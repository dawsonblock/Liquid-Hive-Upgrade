# Contributing to Liquid-Hive-Upgrade

Thank you for your interest in contributing to Liquid-Hive-Upgrade! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Style and Standards](#code-style-and-standards)
- [Testing Requirements](#testing-requirements)
- [Submitting Changes](#submitting-changes)
- [Security Considerations](#security-considerations)
- [Community and Support](#community-and-support)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@liquid-hive.dev.

## Getting Started

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** and **Yarn**
- **Docker** and **Docker Compose**
- **Git**
- **Make** (for development commands)

### Development Setup

1. **Fork and Clone the Repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/liquid-hive-upgrade.git
   cd liquid-hive-upgrade
   ```

2. **Set Up Development Environment**

   ```bash
   # Install all dependencies and set up pre-commit hooks
   make install

   # Create environment file from template
   make env-create

   # Start development services
   make up-dev
   ```

3. **Verify Installation**

   ```bash
   # Run health checks
   make health

   # Run basic tests
   make test-unit
   ```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **💡 Feature Requests**: Suggest new functionality
- **📝 Documentation**: Improve our docs and examples
- **🔧 Code Contributions**: Submit bug fixes and new features
- **🧪 Testing**: Add test cases and improve coverage
- **🎨 UI/UX**: Enhance the frontend experience
- **🔒 Security**: Report vulnerabilities responsibly

### Before You Start

1. **Check Existing Issues**: Search for existing issues before creating new ones
2. **Discuss Major Changes**: Open an issue for significant changes before coding
3. **Follow Project Direction**: Ensure your contribution aligns with project goals
4. **Read Documentation**: Familiarize yourself with the codebase and architecture

## Development Workflow

### Branch Naming Convention

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test improvements
- `security/description` - Security improvements

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `perf`: Performance improvements
- `security`: Security-related changes

**Examples:**

```
feat(arena): add model comparison endpoint
fix(auth): resolve JWT validation issue
docs(api): update OpenAPI specifications
test(planner): add integration tests for DAG execution
```

## Code Style and Standards

### Python Code Style

- **Formatter**: Ruff (primary) + Black (backup)
- **Linter**: Ruff with comprehensive rule set
- **Type Checking**: MyPy with strict configuration
- **Line Length**: 100 characters
- **Docstrings**: Google style

**Key Rules:**

```python
# Good
def process_task(task_id: str, options: TaskOptions) -> TaskResult:
    """Process a task with the given options.

    Args:
        task_id: Unique identifier for the task
        options: Configuration options for processing

    Returns:
        Result of the task processing

    Raises:
        TaskError: If task processing fails
    """
    pass

# Avoid
def process_task(task_id, options):
    pass
```

### Frontend Code Style

- **Formatter**: Prettier
- **Linter**: ESLint with TypeScript and React rules
- **Type Checking**: TypeScript strict mode
- **Component Style**: Functional components with hooks

**Key Rules:**

```typescript
// Good
interface Props {
  userId: string;
  onUpdate: (user: User) => void;
}

const UserComponent: React.FC<Props> = ({ userId, onUpdate }) => {
  // Component implementation
};

// Avoid
const UserComponent = (props: any) => {
  // Implementation
};
```

### Code Quality Checks

All contributions must pass:

```bash
# Run all quality checks
make check

# Individual checks
make lint          # Linting
make security      # Security analysis
make complexity    # Code complexity
make test-unit     # Unit tests
```

## Testing Requirements

### Test Categories

1. **Unit Tests** - Test individual functions/classes
2. **Integration Tests** - Test component interactions
3. **Security Tests** - Test security features
4. **Performance Tests** - Benchmark critical paths

### Testing Standards

- **Coverage**: Minimum 70% code coverage for new code
- **Test Naming**: Descriptive names explaining what is tested
- **Test Structure**: Arrange-Act-Assert pattern
- **Mocking**: Use appropriate mocking for external dependencies

### Writing Tests

```python
# Good test example
def test_task_execution_with_valid_input():
    # Arrange
    task = TaskNode(id="test", operation="add", params={"a": 1, "b": 2})
    executor = PlanExecutor()

    # Act
    result = executor.execute_task(task)

    # Assert
    assert result.success is True
    assert result.output == 3

# Frontend test example
describe('UserComponent', () => {
  it('should display user information correctly', () => {
    const mockUser = { id: '1', name: 'Test User' };
    render(<UserComponent user={mockUser} />);

    expect(screen.getByText('Test User')).toBeInTheDocument();
  });
});
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-parallel

# Run with coverage
pytest --cov=src --cov-report=html tests/
```

## Submitting Changes

### Pull Request Process

1. **Create Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**

   - Write code following our standards
   - Add/update tests
   - Update documentation if needed

3. **Run Quality Checks Locally**

   ```bash
   make pre-commit
   make check
   ```

4. **Commit Changes**

   ```bash
   git add .
   git commit -m "feat(scope): add new feature"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

### Pull Request Requirements

**Required:**

- [ ] All tests pass
- [ ] Code coverage maintained/improved
- [ ] Documentation updated
- [ ] CHANGELOG entry added (for significant changes)
- [ ] Security implications considered
- [ ] Performance impact assessed

**PR Description Template:**

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
```

### Review Process

1. **Automated Checks**: CI pipeline runs all tests and quality checks
2. **Code Review**: At least one maintainer reviews the code
3. **Security Review**: Security-sensitive changes get additional review
4. **Final Approval**: Maintainer approves and merges

## Security Considerations

### Security-First Development

- **Input Validation**: Always validate and sanitize user inputs
- **Authentication**: Implement proper authentication and authorization
- **Secrets Management**: Never commit secrets; use environment variables
- **Dependencies**: Keep dependencies updated and scan for vulnerabilities
- **Logging**: Be careful not to log sensitive information

### Reporting Security Issues

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, report security issues via email to: **security@liquid-hive.dev**

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

### Security Tools

We use several security tools:

```bash
# Security analysis
make security

# Dependency scanning
make update-deps

# Secrets detection
detect-secrets scan --baseline .secrets.baseline
```

## Architecture and Design Principles

### Core Principles

1. **Modularity**: Code should be modular and reusable
2. **Testability**: Design code to be easily testable
3. **Security**: Security considerations in every design decision
4. **Performance**: Optimize for performance where it matters
5. **Maintainability**: Write code that's easy to maintain and understand

### Architecture Overview

```
liquid-hive-upgrade/
├── src/
│   ├── unified_runtime/     # Core FastAPI application
│   ├── capsule_brain/       # Planner and DAG execution
│   ├── oracle/              # LLM provider interface
│   └── internet_agent_advanced/  # Advanced internet agent
├── frontend/                # React TypeScript frontend
├── tests/                   # Comprehensive test suite
├── helm/                    # Kubernetes deployment
└── config/                  # Configuration files
```

### Key Components

- **Unified Runtime**: Core FastAPI server with routing
- **Oracle Providers**: Swappable LLM provider interface
- **Planner**: DAG-based task execution engine
- **Arena**: Model evaluation and comparison service
- **Security Layer**: Authentication and authorization

## Documentation Standards

### Code Documentation

- **Docstrings**: All public functions, classes, and modules
- **Type Hints**: Comprehensive type annotations
- **Comments**: Complex logic should be commented
- **README**: Each major component should have a README

### API Documentation

- **OpenAPI**: Auto-generated from FastAPI code
- **Examples**: Include request/response examples
- **Error Codes**: Document all possible error responses

### Architecture Documentation

- **ADRs**: Document architectural decisions
- **Diagrams**: Use diagrams for complex architectures
- **Runbooks**: Operational procedures and troubleshooting

## Performance Guidelines

### Performance Considerations

- **Database Queries**: Optimize queries and use proper indexing
- **Caching**: Implement appropriate caching strategies
- **Async/Await**: Use async patterns for I/O operations
- **Resource Usage**: Monitor memory and CPU usage
- **Scalability**: Design for horizontal scaling

### Benchmarking

```bash
# Run performance benchmarks
make benchmark

# Profile application
make profile
```

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped
- [ ] Security review completed
- [ ] Performance impact assessed
- [ ] Deployment tested

## Community and Support

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Documentation**: Check our comprehensive docs
- **Email**: For security issues and private concerns

### Communication Channels

- **GitHub**: Primary development platform
- **Discord**: Community chat (coming soon)
- **Email**: security@liquid-hive.dev for security issues

### Recognition

Contributors are recognized in:

- GitHub contributors list
- CHANGELOG.md for significant contributions
- Project documentation
- Release notes

## Development Tips

### Useful Commands

```bash
# Development workflow
make install          # Set up development environment
make test            # Run all tests
make lint            # Check code quality
make format          # Format code
make security        # Security analysis
make up-dev          # Start development services
make logs            # View service logs

# Docker operations
make docker-build    # Build Docker image
make docker-run      # Run container locally
make up              # Start all services
make down            # Stop all services

# Documentation
make docs            # Generate documentation
make docs-serve      # Serve docs locally
```

### IDE Setup

**VS Code Extensions:**

- Python
- Pylance
- Ruff
- Black Formatter
- TypeScript and JavaScript Language Features
- ESLint
- Prettier

**PyCharm/IntelliJ:**

- Configure interpreters for Python 3.11
- Enable type checking
- Configure code style to match our standards

### Troubleshooting

**Common Issues:**

- **Import Errors**: Check PYTHONPATH configuration
- **Test Failures**: Ensure services are running (`make up-dev`)
- **Linting Errors**: Run `make format` to auto-fix
- **Type Errors**: Check type annotations and imports

**Getting Unstuck:**

1. Check existing issues on GitHub
2. Review documentation
3. Ask in discussions
4. Reach out to maintainers

## Final Notes

### Before Your First Contribution

- [ ] Read and understand the Code of Conduct
- [ ] Set up your development environment
- [ ] Run the test suite successfully
- [ ] Make a small test change to verify your setup

### Thank You

Thank you for contributing to Liquid-Hive-Upgrade! Your contributions help make this project better for everyone. We appreciate your time and effort in helping us build a robust, secure, and scalable system.

---

**Questions?** Feel free to open an issue for clarification or reach out to the maintainers.

**Happy Contributing!** 🚀
