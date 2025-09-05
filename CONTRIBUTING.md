# 🤝 Contributing to Liquid Hive

Thank you for your interest in contributing to Liquid Hive! This document provides guidelines and information for contributors.

## 🎯 How to Contribute

### **Types of Contributions**

We welcome various types of contributions:

- 🐛 **Bug Reports**: Help us identify and fix issues
- 💡 **Feature Requests**: Suggest new capabilities  
- 📝 **Documentation**: Improve guides and API docs
- 🧪 **Testing**: Add test coverage and scenarios
- 🔧 **Code**: Implement features and bug fixes
- 🎨 **UI/UX**: Enhance user interface and experience
- 📊 **Performance**: Optimize algorithms and infrastructure

### **Getting Started**

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/liquid-hive.git
   cd liquid-hive
   ```
3. **Set up** development environment:
   ```bash
   make dev-setup
   ```
4. **Create** a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Workflow

### **Before You Start**

- Check existing [issues](https://github.com/liquid-hive/liquid-hive/issues) and [discussions](https://github.com/liquid-hive/liquid-hive/discussions)
- For major features, open a discussion first to align on approach
- Ensure your development environment passes all tests: `make test`

### **Development Process**

1. **Write Code**
   - Follow our [code standards](#code-standards)
   - Add tests for new functionality
   - Update documentation as needed

2. **Test Locally**
   ```bash
   make test           # Run full test suite
   make lint           # Check code quality  
   make security       # Security checks
   make health         # Verify services work
   ```

3. **Commit Changes**
   - Use clear, descriptive commit messages
   - Follow [conventional commits](https://www.conventionalcommits.org/) format:
     ```
     feat: add feedback loop engine
     fix: resolve memory leak in agent pool
     docs: update API documentation
     test: add integration tests for oracle system
     ```

4. **Submit Pull Request**
   - Push to your fork and create a pull request
   - Fill out the PR template completely
   - Link related issues and discussions
   - Request review from maintainers

## 📏 Code Standards

### **Python Standards**

**Formatting & Linting:**
```bash
# Format code
ruff format .

# Check linting
ruff check .

# Type checking
mypy src/ apps/
```

**Key Requirements:**
- **Line Length**: 100 characters maximum
- **Import Order**: Follow isort configuration  
- **Type Hints**: Required for all public functions
- **Docstrings**: Google-style docstrings for classes and functions
- **Test Coverage**: Minimum 80% coverage for new code

**Example:**
```python
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()

class AgentProcessor:
    """Processes agent requests with error handling.
    
    This class manages the lifecycle of agent processing requests,
    including validation, execution, and response formatting.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize processor with configuration.
        
        Args:
            config: Configuration dictionary containing processor settings
        """
        self.config = config
        self._initialized = False
    
    async def process_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process agent request and return response.
        
        Args:
            request_data: The incoming request data to process
            
        Returns:
            Processed response data, or None if processing failed
            
        Raises:
            ValueError: If request_data is invalid
            ProcessingError: If processing fails
        """
        if not self._validate_request(request_data):
            raise ValueError("Invalid request data format")
        
        try:
            result = await self._execute_processing(request_data)
            logger.info("Request processed successfully", request_id=request_data.get("id"))
            return result
        except Exception as e:
            logger.error("Processing failed", error=str(e))
            raise ProcessingError(f"Failed to process request: {e}") from e
```

### **TypeScript/React Standards**

**Configuration:**
- ESLint with TypeScript rules
- Prettier for formatting
- Strict type checking enabled

**Key Requirements:**
```typescript
// Use explicit types
interface AgentResponse {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  data?: any;
  error?: string;
}

// Use React hooks properly
const useAgentState = (agentId: string): AgentResponse | null => {
  const [state, setState] = useState<AgentResponse | null>(null);
  
  useEffect(() => {
    const fetchAgentState = async () => {
      try {
        const response = await api.get(`/agents/${agentId}`);
        setState(response.data);
      } catch (error) {
        console.error('Failed to fetch agent state:', error);
      }
    };
    
    fetchAgentState();
  }, [agentId]);
  
  return state;
};

// Component with proper typing
interface AgentCardProps {
  agent: AgentResponse;
  onUpdate: (id: string) => void;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent, onUpdate }) => {
  return (
    <div className="agent-card">
      <h3>{agent.id}</h3>
      <p>Status: {agent.status}</p>
      {agent.error && <p className="error">{agent.error}</p>}
    </div>
  );
};
```

### **Testing Standards**

**Python Testing:**
```python
import pytest
from unittest.mock import Mock, patch
from apps.api.main import app
from fastapi.testclient import TestClient

class TestAgentProcessor:
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_agent_processor(self):
        with patch('src.hivemind.agent_processor.AgentProcessor') as mock:
            yield mock
    
    async def test_process_request_success(self, mock_agent_processor):
        """Test successful request processing."""
        # Arrange
        mock_processor = Mock()
        mock_processor.process_request.return_value = {"status": "completed"}
        mock_agent_processor.return_value = mock_processor
        
        request_data = {"id": "test-123", "type": "query"}
        
        # Act
        result = await mock_processor.process_request(request_data)
        
        # Assert
        assert result["status"] == "completed"
        mock_processor.process_request.assert_called_once_with(request_data)
    
    async def test_process_request_invalid_data(self, mock_agent_processor):
        """Test handling of invalid request data."""
        mock_processor = Mock()
        mock_processor.process_request.side_effect = ValueError("Invalid data")
        mock_agent_processor.return_value = mock_processor
        
        with pytest.raises(ValueError, match="Invalid data"):
            await mock_processor.process_request({})
```

**Frontend Testing:**
```typescript
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AgentCard } from './AgentCard';

describe('AgentCard', () => {
  const mockAgent = {
    id: 'test-agent-123',
    status: 'completed' as const,
    data: { result: 'test result' }
  };
  
  const mockOnUpdate = jest.fn();
  
  beforeEach(() => {
    mockOnUpdate.mockClear();
  });
  
  it('renders agent information correctly', () => {
    render(<AgentCard agent={mockAgent} onUpdate={mockOnUpdate} />);
    
    expect(screen.getByText('test-agent-123')).toBeInTheDocument();
    expect(screen.getByText('Status: completed')).toBeInTheDocument();
  });
  
  it('displays error message when agent has error', () => {
    const errorAgent = { ...mockAgent, error: 'Processing failed' };
    
    render(<AgentCard agent={errorAgent} onUpdate={mockOnUpdate} />);
    
    expect(screen.getByText('Processing failed')).toBeInTheDocument();
    expect(screen.getByText('Processing failed')).toHaveClass('error');
  });
  
  it('calls onUpdate when refresh button clicked', async () => {
    render(<AgentCard agent={mockAgent} onUpdate={mockOnUpdate} />);
    
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshButton);
    
    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith('test-agent-123');
    });
  });
});
```

## 🧪 Testing Guidelines

### **Test Categories**

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions and classes
   - Fast execution (< 1 second each)
   - No external dependencies
   - Minimum 80% coverage required

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - May use test databases/services
   - Validate API contracts
   - End-to-end workflows

3. **Performance Tests** (`tests/performance/`)
   - Load testing with k6
   - Response time validation
   - Resource usage monitoring
   - Scalability verification

### **Running Tests**

```bash
# All tests
make test

# Specific test categories  
make test-unit
make test-integration
pytest tests/performance/

# Coverage reporting
pytest --cov=src --cov=apps --cov-report=html

# Frontend tests
cd frontend && yarn test --coverage
```

### **Test Data Management**

- Use factories for test data generation
- Clean up resources after tests
- Use separate test databases
- Mock external API calls

## 📝 Documentation Guidelines

### **Documentation Types**

1. **Code Documentation**
   - Inline comments for complex logic
   - Docstrings for all public APIs
   - Type hints for function signatures

2. **API Documentation**
   - OpenAPI/Swagger specifications
   - Example requests/responses
   - Error code explanations

3. **User Documentation**
   - Setup and installation guides
   - Usage examples and tutorials
   - Troubleshooting guides

### **Writing Guidelines**

- **Clear and Concise**: Use simple, direct language
- **Examples**: Provide code examples for concepts
- **Structure**: Use headings, lists, and formatting consistently
- **Accuracy**: Keep documentation synchronized with code changes

## 🚦 Pull Request Process

### **PR Requirements**

Before submitting a pull request, ensure:

- [ ] **Tests Pass**: All existing tests continue to pass
- [ ] **New Tests**: New functionality has adequate test coverage
- [ ] **Linting**: Code passes all linting checks
- [ ] **Documentation**: README and docs updated as needed
- [ ] **Security**: No secrets or sensitive data committed
- [ ] **Performance**: No significant performance regressions

### **PR Template**

```markdown
## Description
Brief description of the changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
```

### **Review Process**

1. **Automated Checks**: CI pipeline runs automatically
2. **Maintainer Review**: Core team reviews code and design
3. **Feedback**: Address review comments promptly
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainers merge approved PRs

## 🌍 Community Guidelines

### **Code of Conduct**

We are committed to fostering an open and welcoming environment. All participants are expected to:

- **Be Respectful**: Treat all community members with respect
- **Be Inclusive**: Welcome newcomers and diverse perspectives  
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Professional**: Maintain professional communication standards

### **Communication Channels**

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and collaboration
- **Email**: Security issues and sensitive topics

## 🏆 Recognition

We appreciate all contributors! Recognition includes:

- **Contributors File**: Listed in CONTRIBUTORS.md
- **Release Notes**: Contributions highlighted in releases
- **Social Media**: Major contributions shared on social platforms
- **Swag**: Stickers and merchandise for significant contributors

## ❓ Questions?

If you have questions about contributing:

1. Check existing [documentation](docs/)
2. Search [GitHub issues](https://github.com/liquid-hive/liquid-hive/issues)
3. Start a [discussion](https://github.com/liquid-hive/liquid-hive/discussions)
4. Contact maintainers directly

---

**Thank you for contributing to Liquid Hive!** 🚀

Your contributions help build the future of AI agent platforms.