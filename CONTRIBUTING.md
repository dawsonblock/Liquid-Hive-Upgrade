# 🤝 Contributing to Liquid-Hive

Thank you for your interest in contributing to Liquid-Hive! This guide will help you get started with development and ensure your contributions follow our standards.

## 🚀 Quick Start

### **Prerequisites**

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Git

### **Development Setup**

```bash
# 1. Fork and clone
git clone https://github.com/your-username/liquid-hive.git
cd liquid-hive

# 2. Set up development environment
make dev-setup

# 3. Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 4. Start development services
make quick-start
```

## 📋 Development Workflow

### **1. Create Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements

### **2. Make Changes**

Follow our coding standards:

#### **Python Code Standards**
- Use `ruff` for linting and formatting
- Follow Google docstring style
- Type hints required for all functions
- Maximum line length: 100 characters
- Import organization with `isort`

```python
def process_query(query: str, max_tokens: int = 1000) -> Dict[str, Any]:
    """Process a user query through the AI pipeline.
    
    Args:
        query: The user's input query
        max_tokens: Maximum tokens in response
        
    Returns:
        Dictionary containing response and metadata
        
    Raises:
        ValueError: If query is empty or invalid
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
    
    return {"response": "processed", "tokens": 42}
```

#### **Frontend Code Standards**
- TypeScript strict mode enabled
- React functional components with hooks
- ESLint + Prettier formatting
- Component naming: PascalCase
- File naming: kebab-case

```typescript
interface ChatMessageProps {
  message: string;
  timestamp: Date;
  isUser: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  timestamp, 
  isUser 
}) => {
  return (
    <div className={`message ${isUser ? 'user' : 'bot'}`}>
      <p>{message}</p>
      <time>{timestamp.toLocaleString()}</time>
    </div>
  );
};
```

### **3. Testing**

Before committing, ensure all tests pass:

```bash
# Run all tests
make test

# Run specific test suites
make test-python    # Backend tests only
make test-frontend  # Frontend tests only
make test-smoke     # Integration tests
```

#### **Writing Tests**

**Python Tests (pytest)**
```python
import pytest
from src.unified_runtime.processor import process_query

class TestQueryProcessor:
    def test_valid_query(self):
        result = process_query("What is Python?")
        assert "response" in result
        assert result["tokens"] > 0
    
    def test_empty_query_raises_error(self):
        with pytest.raises(ValueError, match="Query cannot be empty"):
            process_query("")
```

**Frontend Tests (Jest + RTL)**
```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatMessage } from './ChatMessage';

describe('ChatMessage', () => {
  test('renders user message correctly', () => {
    render(
      <ChatMessage 
        message="Hello world" 
        timestamp={new Date('2023-01-01')} 
        isUser={true} 
      />
    );
    
    expect(screen.getByText('Hello world')).toBeInTheDocument();
    expect(screen.getByText('1/1/2023')).toBeInTheDocument();
  });
});
```

### **4. Code Quality Checks**

Run quality checks before committing:

```bash
# Linting
make lint

# Auto-fix issues
make lint-fix

# Code formatting
make format

# Type checking
make type-check

# Security scanning
make security-scan
```

### **5. Commit Guidelines**

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: add voice input support to chat interface"
git commit -m "fix: resolve memory leak in capsule brain"
git commit -m "docs: update deployment guide with Kubernetes examples"
git commit -m "test: add integration tests for oracle pipeline"
```

**Commit types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting changes
- `refactor`: Code restructuring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

### **6. Submit Pull Request**

```bash
# Push your branch
git push origin feature/your-feature-name

# Create PR on GitHub with:
# - Clear title and description
# - Link to related issues
# - Screenshots for UI changes
# - Checklist completion
```

## 📝 Pull Request Template

```markdown
## 📋 Description
Brief description of changes and motivation.

## 🔗 Related Issues
Fixes #123, Closes #456

## 🧪 Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## 📷 Screenshots (if applicable)
[Add screenshots for UI changes]

## ✅ Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## 🏗️ Architecture Guidelines

### **Backend Architecture**

```
src/
├── unified_runtime/     # FastAPI application entry point
│   ├── server.py       # Main FastAPI app
│   ├── routes/         # API route handlers
│   └── middleware/     # Custom middleware
├── capsule_brain/      # Memory and knowledge systems
├── hivemind/           # Multi-agent reasoning
├── oracle/             # Quality assurance pipeline
└── safety/             # Security and validation
```

### **Frontend Architecture**

```
frontend/src/
├── components/         # Reusable UI components
│   ├── common/        # Shared components
│   ├── chat/          # Chat-specific components
│   └── admin/         # Admin interface components
├── services/          # API clients and utilities
├── hooks/            # Custom React hooks
├── store/            # Redux state management
└── utils/            # Helper functions
```

## 🚨 Security Guidelines

### **Input Validation**
Always validate and sanitize user inputs:

```python
from pydantic import BaseModel, validator

class ChatRequest(BaseModel):
    query: str
    max_tokens: int = 1000
    
    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()[:10000]  # Limit length
```

### **Secret Management**
- Never commit secrets to version control
- Use environment variables for configuration
- Validate all environment variables on startup

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str
    jwt_secret: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### **API Security**
- Input validation on all endpoints
- Rate limiting for public endpoints
- Authentication/authorization where needed
- CORS configuration
- Security headers

## 🧪 Testing Strategy

### **Test Types**

1. **Unit Tests** - Test individual functions/components
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test complete user workflows
4. **Performance Tests** - Test response times and load
5. **Security Tests** - Test for vulnerabilities

### **Testing Best Practices**

- Write tests before fixing bugs (TDD)
- Test edge cases and error conditions
- Use descriptive test names
- Keep tests isolated and deterministic
- Mock external dependencies

### **Coverage Goals**

- **Backend**: 80%+ line coverage
- **Frontend**: 70%+ line coverage
- **Critical paths**: 100% coverage

## 📊 Performance Guidelines

### **Backend Performance**
- Async/await for I/O operations
- Database query optimization
- Caching frequently accessed data
- Connection pooling
- Background tasks for heavy operations

### **Frontend Performance**
- Code splitting and lazy loading
- Memoization for expensive calculations
- Virtualization for large lists
- Optimize bundle size
- Use production builds

## 🚀 Release Process

### **Version Management**
We use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Breaking changes increment MAJOR
- New features increment MINOR
- Bug fixes increment PATCH

### **Release Checklist**
1. All tests passing
2. Documentation updated
3. CHANGELOG.md updated
4. Security scan clean
5. Performance benchmarks acceptable
6. Deployment tested in staging

## 🤔 Getting Help

### **Communication Channels**
- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and ideas
- **Discord** - Real-time development chat [link]

### **Documentation**
- [Architecture Overview](docs/architecture/)
- [API Documentation](docs/api/)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Security Policy](SECURITY.md)

### **Common Questions**

**Q: How do I debug the AI pipeline locally?**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
make start-backend
```

**Q: How do I test with real AI models?**
```bash
# Set up test API keys in .env.test
export OPENAI_API_KEY=your-test-key
pytest tests/integration/
```

**Q: How do I contribute to documentation?**
```bash
# Edit markdown files in docs/
# Preview locally
make docs-serve
# Submit PR with doc changes
```

## 📜 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive environment for all contributors.

## 🏆 Recognition

Contributors are recognized in:
- GitHub contributor graphs
- Release notes acknowledgments
- Optional contributor hall of fame
- Community Discord recognition

---

**Thank you for contributing to Liquid-Hive! 🧠⚡**

Every contribution, whether code, documentation, testing, or feedback, helps make this project better for everyone.