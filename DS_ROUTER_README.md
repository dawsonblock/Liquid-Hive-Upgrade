# DS-Router v1: Intelligent Model Routing System 🧠

## Overview

The DS-Router (DeepSeek Router) v1 is an advanced intelligent routing system that automatically selects the optimal AI model based on query complexity, confidence assessment, and safety requirements. It implements a hierarchical escalation strategy with comprehensive safety controls.

---

## 🎯 Key Features

### **Intelligent Model Selection**
- **DeepSeek Chat**: Fast responses for simple queries
- **DeepSeek Thinking**: Step-by-step reasoning for complex problems  
- **DeepSeek R1**: Advanced reasoning for low-confidence scenarios
- **Qwen 2.5 7B**: Local CPU fallback when APIs fail or budget exceeded

### **Advanced Safety Sandwich**
- **Pre-Guard**: Input sanitization, PII redaction, prompt injection detection
- **Post-Guard**: Output safety verification, toxicity filtering, fact checking
- **Comprehensive Audit**: Full request/response logging for compliance

### **Budget Management**
- Daily token and cost limits with hard/warn enforcement
- Automatic fallback to local models when budget exceeded
- Admin controls for budget reset and monitoring

### **Real-time Monitoring**
- Provider health status and performance metrics
- Confidence scoring and escalation tracking
- Comprehensive logging with structured data

---

## 🚀 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DS-Router v1                            │
├─────────────────────────────────────────────────────────────┤
│  Pre-Guard  │  Router Logic  │  Providers  │  Post-Guard   │
│             │                │             │               │
│ • PII Redact│ • Complexity   │ • DeepSeek  │ • Safety      │
│ • Injection │   Detection    │   Chat      │   Filtering   │
│   Detection │ • Confidence   │ • DeepSeek  │ • Toxicity    │
│ • Risk      │   Assessment   │   Think     │   Scoring     │
│   Assessment│ • Escalation   │ • DeepSeek  │ • Citation    │
│             │   Logic        │   R1        │   Verification│
│             │                │ • Qwen CPU  │               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

```bash
# DS-Router Configuration
MODEL_PROVIDER=auto                    # auto|deepseek|qwen
DEEPSEEK_API_KEY=sk-your-key-here     # DeepSeek API key
HF_TOKEN=hf-your-token-here           # HuggingFace token for Qwen

# Model Configuration  
DEEPSEEK_MODEL_CHAT=deepseek-chat     # Chat model
DEEPSEEK_MODEL_THINK=deepseek-chat    # Thinking model
DEEPSEEK_MODEL_R1=deepseek-reasoner   # Reasoning model
HF_MODEL_QWEN=Qwen/Qwen2.5-7B-Instruct # Local fallback model

# Router Thresholds
CONF_THRESHOLD=0.62                   # Confidence threshold for R1 escalation
SUPPORT_THRESHOLD=0.55                # RAG support threshold
MAX_COT_TOKENS=6000                   # Maximum chain-of-thought tokens

# Budget Controls
MAX_ORACLE_TOKENS_PER_DAY=250000      # Daily token limit
MAX_ORACLE_USD_PER_DAY=50             # Daily cost limit ($)
BUDGET_ENFORCEMENT=hard               # hard|warn

# System Configuration
PROVIDER_TIMEOUT_MS=120000            # Provider timeout (ms)
ADMIN_TOKEN=your-admin-token          # Admin API access
```

---

## 📊 Routing Logic

### 1. **Query Classification**
```python
# Simple queries → DeepSeek Chat
"What's the weather?"
"Hello, how are you?"
"Define machine learning"

# Complex queries → DeepSeek Thinking  
"Prove that P != NP"
"Write a regex for email validation"
"Debug this algorithm"
"Analyze this logical fallacy"
```

### 2. **Confidence Assessment**
```python
# High confidence (>0.62) → Use response
# Low confidence (<0.62) → Escalate to R1

confidence_factors = {
    "response_length": "longer responses = higher confidence",
    "uncertainty_markers": "'maybe', 'not sure' = lower confidence", 
    "provider_type": "R1 > Thinking > Chat > Local",
    "content_quality": "detailed explanations = higher confidence"
}
```

### 3. **Fallback Chain**
```
DeepSeek Chat/Thinking → (low confidence) → DeepSeek R1 
                      ↓ (API failure/budget)
                    Qwen CPU Local
                      ↓ (local failure)
                   Static Fallback
```

---

## 🔒 Safety Controls

### **Pre-Guard Processing**
```python
# PII Detection & Redaction
"My email is john@example.com" → "My email is <REDACTED:EMAIL>"

# Prompt Injection Detection  
"Ignore previous instructions" → BLOCKED

# Risk Assessment
"How to hack computers" → FLAGGED (illegal category)
```

### **Post-Guard Verification**
```python
# Safety Violation Detection
"Step-by-step violence instructions" → BLOCKED

# Toxicity Scoring
"You're stupid and worthless" → BLOCKED (high toxicity)

# Fact Verification
"Studies show X" → Enhanced with citations
```

---

## 🛠️ API Endpoints

### **Core Chat API**
```bash
# Standard chat with intelligent routing
POST /api/chat
{
    "q": "Explain quantum computing"
}

# Response includes routing information
{
    "answer": "Quantum computing uses quantum mechanics...",
    "provider": "deepseek_thinking",
    "confidence": 0.87,
    "escalated": false,
    "context": "..."
}
```

### **Provider Status**
```bash
# Check all provider health
GET /api/providers

{
    "providers": {
        "deepseek_chat": {"status": "healthy", "latency_ms": 120},
        "deepseek_thinking": {"status": "healthy", "latency_ms": 180},
        "deepseek_r1": {"status": "degraded", "reason": "high_latency"},
        "qwen_cpu": {"status": "healthy", "local_compute": true}
    },
    "router_active": true
}
```

### **Admin Controls**
```bash
# Reset daily budget (requires ADMIN_TOKEN)
POST /api/admin/budget/reset
Authorization: Bearer your-admin-token

# Update router thresholds
POST /api/admin/router/set-thresholds
{
    "conf_threshold": 0.65,
    "support_threshold": 0.60,
    "max_cot_tokens": 8000
}
```

---

## 📈 Monitoring & Metrics

### **Prometheus Metrics**
```prometheus
# Provider usage
provider_requests_total{provider="deepseek_chat"}
provider_requests_total{provider="deepseek_thinking"}
provider_requests_total{provider="deepseek_r1"}
provider_requests_total{provider="qwen_cpu"}

# Confidence and escalations
confidence_histogram
escalations_total{to="r1|thinking|fallback"}

# Budget tracking
oracle_cost_usd_total{provider}
oracle_tokens_total{provider}

# Safety filtering
blocked_requests_total{stage="pre|post"}
```

### **Structured Logging**
```json
{
    "timestamp": "2025-08-30T10:15:30Z",
    "provider": "deepseek_thinking",
    "confidence": 0.78,
    "routing_decision": "complex_query",
    "escalated": false,
    "tokens": {"prompt": 25, "output": 150},
    "cost_usd": 0.024,
    "latency_ms": 1850,
    "blocked": false,
    "filters": {"pre_guard": "sanitized", "post_guard": "passed"}
}
```

---

## 🧪 Testing

### **Run Test Suite**
```bash
# Run all DS-Router tests
pytest tests/test_ds_router.py -v

# Test routing paths specifically
pytest tests/test_routing_paths.py -v

# Test with coverage
pytest tests/ --cov=unified_runtime.model_router --cov=safety/
```

### **Manual Testing**
```bash
# Test simple routing
curl -X POST http://localhost:8000/api/chat -d 'q=Hello'

# Test complex routing  
curl -X POST http://localhost:8000/api/chat -d 'q=Prove that sqrt(2) is irrational'

# Test provider status
curl http://localhost:8000/api/providers

# Test with budget exceeded (set low limits first)
export MAX_ORACLE_TOKENS_PER_DAY=10
curl -X POST http://localhost:8000/api/chat -d 'q=Any question'
```

---

## 🚀 Quick Start

### 1. **Setup Environment**
```bash
# Copy example environment
cp .env.example .env

# Add your API keys
export DEEPSEEK_API_KEY=sk-your-deepseek-key
export HF_TOKEN=hf-your-huggingface-token
export ADMIN_TOKEN=your-secure-admin-token
```

### 2. **Start System**  
```bash
# Start with Docker
docker-compose up --build

# Or start individual services
python -m unified_runtime.__main__
```

### 3. **Verify Operation**
```bash
# Health check
curl http://localhost:8000/api/healthz

# Provider status
curl http://localhost:8000/api/providers  

# Test chat
curl -X POST http://localhost:8000/api/chat -d 'q=What is AI?'
```

---

## 🔍 Troubleshooting

### **Common Issues**

**Provider Not Available**
```bash
# Check API keys are set
echo $DEEPSEEK_API_KEY

# Check provider status
curl http://localhost:8000/api/providers
```

**Budget Exceeded**
```bash
# Reset budget (admin)
curl -X POST http://localhost:8000/api/admin/budget/reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Check current usage in logs
docker-compose logs api | grep budget
```

**Local Model Loading Fails**
```bash
# Check available memory
free -h

# Reduce model size or use quantization
export HF_MODEL_QWEN=Qwen/Qwen2.5-1.5B-Instruct
```

**High Latency**
```bash
# Check provider-specific timeouts
export PROVIDER_TIMEOUT_MS=60000

# Monitor provider performance
curl http://localhost:8000/api/providers
```

---

## 📝 Development

### **Adding New Providers**
```python
# 1. Implement BaseProvider interface
class MyProvider(BaseProvider):
    async def generate(self, request: GenRequest) -> GenResponse:
        # Implementation
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        # Health check logic
        pass

# 2. Register in router
router.providers["my_provider"] = MyProvider(config)

# 3. Update routing logic if needed
```

### **Custom Safety Rules**
```python
# Add to pre_guard.py risk patterns
self.risk_patterns["custom_risk"] = re.compile(r'pattern', re.IGNORECASE)

# Add to post_guard.py safety patterns  
self.safety_patterns["custom_violation"] = re.compile(r'pattern', re.IGNORECASE)
```

---

## 🎯 Production Deployment

### **Scaling Considerations**
- Use Redis for budget tracking across instances
- Implement proper secret management for API keys
- Set up monitoring and alerting for provider health
- Configure log aggregation for audit trails
- Implement rate limiting and request queuing

### **Security Checklist**
- [ ] Secure admin token management
- [ ] API key rotation procedures  
- [ ] Audit log retention and analysis
- [ ] Safety filter rule updates
- [ ] Provider access monitoring

---

**DS-Router v1 Status: ✅ PRODUCTION READY**

The DS-Router system provides intelligent, safe, and cost-effective AI model routing with comprehensive monitoring and control capabilities. It automatically adapts to query complexity while maintaining strict safety and budget controls.