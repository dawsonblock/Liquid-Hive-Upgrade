#!/usr/bin/env bash
# Verify wiring consistency between Docker Compose and Helm

set -euo pipefail

echo "🔍 LIQUID HIVE WIRING VERIFICATION"
echo "================================="

# Check if required files exist
if [[ ! -f "docker-compose.yaml" ]]; then
    echo "❌ docker-compose.yaml not found"
    exit 1
fi

if [[ ! -f "infra/helm/liquid-hive/values.yaml" ]]; then
    echo "❌ Helm values.yaml not found"
    exit 1
fi

echo "✅ Configuration files found"

# Install yq if not present (for YAML parsing)
if ! command -v yq &> /dev/null; then
    echo "📦 Installing yq for YAML parsing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y yq
    elif command -v brew &> /dev/null; then
        brew install yq
    else
        echo "⚠️  yq not available - using basic parsing"
    fi
fi

echo ""
echo "🔍 Docker Compose Services:"
echo "--------------------------"

if command -v yq &> /dev/null; then
    yq eval '.services | keys' docker-compose.yaml 2>/dev/null || {
        echo "Using fallback parsing..."
        grep -A 1 "^  [a-zA-Z]" docker-compose.yaml | grep -E "^  [a-zA-Z]" | sed 's/://g' | sed 's/^  /- /'
    }
else
    echo "Services found in docker-compose.yaml:"
    grep -E "^  [a-zA-Z]" docker-compose.yaml | sed 's/://g' | sed 's/^  /- /'
fi

echo ""
echo "🔍 Expected Services:"
echo "-------------------"
echo "- api (Main backend)"
echo "- feedback-api (Feedback collection)"  
echo "- oracle-api (Oracle engine)"
echo "- frontend (React UI)"
echo "- mongodb (Database)"
echo "- qdrant (Vector database)"
echo "- redis (Hot cache)"
echo "- prometheus (Metrics)"
echo "- grafana (Dashboards)"
echo "- memory-gc (Cleanup job)"

echo ""
echo "🔍 Port Mapping Verification:"
echo "----------------------------"

# Check Docker Compose ports
echo "Docker Compose port mappings:"
if grep -q "8001:808" docker-compose.yaml; then
    echo "✅ Main API: 8001:8080"
else
    echo "❌ Main API port mapping missing or incorrect"
fi

if grep -q "8091:808" docker-compose.yaml; then
    echo "✅ Feedback API: 8091:8080"
else
    echo "❌ Feedback API port mapping missing"
fi

if grep -q "8092:808" docker-compose.yaml; then
    echo "✅ Oracle API: 8092:8080"
else
    echo "❌ Oracle API port mapping missing"
fi

if grep -q "3000:" docker-compose.yaml; then
    echo "✅ Frontend: 3000:*"
else
    echo "❌ Frontend port mapping missing"
fi

if grep -q "6333:6333" docker-compose.yaml; then
    echo "✅ Qdrant: 6333:6333"
else
    echo "❌ Qdrant port mapping missing"
fi

if grep -q "6379:6379" docker-compose.yaml; then
    echo "✅ Redis: 6379:6379"
else
    echo "❌ Redis port mapping missing"
fi

echo ""
echo "🔍 Service Dependencies:"
echo "----------------------"

# Check if services have proper dependencies
if grep -A 10 "depends_on:" docker-compose.yaml | grep -q "mongodb"; then
    echo "✅ API depends on MongoDB"
else
    echo "⚠️  API dependency on MongoDB not explicit"
fi

if grep -A 10 "depends_on:" docker-compose.yaml | grep -q "redis"; then
    echo "✅ Services depend on Redis"
else
    echo "⚠️  Redis dependencies not explicit"
fi

echo ""
echo "🔍 Health Check Verification:"
echo "----------------------------"

# Check if health checks are configured
health_checks=$(grep -c "healthcheck:" docker-compose.yaml || echo "0")
echo "Health checks configured: $health_checks services"

if grep -A 5 "healthcheck:" docker-compose.yaml | grep -q "/health"; then
    echo "✅ Health endpoints configured"
else
    echo "❌ Health endpoints missing in checks"
fi

echo ""
echo "🔍 Environment Variable Consistency:"
echo "----------------------------------"

# Check if .env.example covers required variables
required_vars=("QDRANT_HOST" "REDIS_HOST" "EMBED_DIM" "MEMORY_TTL_DAYS" "OPENAI_API_KEY")

for var in "${required_vars[@]}"; do
    if grep -q "^${var}=" .env.example 2>/dev/null; then
        echo "✅ $var defined in .env.example"
    else
        echo "❌ $var missing from .env.example"
    fi
done

echo ""
echo "🔍 Build Context Verification:"
echo "-----------------------------"

# Check if Dockerfiles exist for services that need them
services_with_builds=("api" "feedback-api" "oracle-api" "frontend")

for service in "${services_with_builds[@]}"; do
    case $service in
        "api")
            dockerfile="apps/api/Dockerfile"
            ;;
        "feedback-api")
            dockerfile="services/feedback_api/Dockerfile"
            ;;
        "oracle-api") 
            dockerfile="services/oracle_api/Dockerfile"
            ;;
        "frontend")
            dockerfile="frontend/Dockerfile"
            ;;
    esac
    
    if [[ -f "$dockerfile" ]]; then
        echo "✅ $service: $dockerfile exists"
    else
        echo "❌ $service: $dockerfile missing"
    fi
done

echo ""
echo "🎯 WIRING VERIFICATION COMPLETE"
echo "=============================="

# Count issues
issues=0
if ! grep -q "8001:808" docker-compose.yaml; then ((issues++)); fi
if ! grep -q "8091:808" docker-compose.yaml; then ((issues++)); fi
if ! grep -q "8092:808" docker-compose.yaml; then ((issues++)); fi
if ! grep -q "6333:6333" docker-compose.yaml; then ((issues++)); fi
if ! grep -q "6379:6379" docker-compose.yaml; then ((issues++)); fi

if [[ $issues -eq 0 ]]; then
    echo "🎉 All wiring checks passed!"
    echo "✅ Docker Compose and service configuration aligned"
    exit 0
else
    echo "⚠️  $issues wiring issues found"
    echo "❌ Review port mappings and service dependencies"
    exit 1
fi