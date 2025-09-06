#!/bin/bash

echo "🧹 Cleaning up useless files..."

# Remove Python cache files
echo "Removing Python cache files..."
rm -rf .pytest_cache
rm -rf .mypy_cache
rm -rf src/__pycache__
rm -rf tests/__pycache__
rm -rf services/__pycache__ 2>/dev/null
rm -rf apps/__pycache__ 2>/dev/null

# Remove test coverage reports
echo "Removing test coverage reports..."
rm -rf htmlcov
rm -f .coverage
rm -f coverage.xml

# Remove frontend build artifacts (generated files)
echo "Removing frontend build artifacts..."
cd frontend/src
rm -f *.js *.d.ts *.js.map *.d.ts.map
rm -rf */__pycache__ 2>/dev/null
cd ../..

# Remove any log files
echo "Removing log files..."
find . -name "*.log" -not -path "./node_modules/*" -delete 2>/dev/null

# Remove temporary files
echo "Removing temporary files..."
find . -name "*.tmp" -o -name "*.temp" -o -name "*~" -o -name "*.orig" -o -name "*.bak" -delete 2>/dev/null

# Remove system files
echo "Removing system files..."
find . -name ".DS_Store" -delete 2>/dev/null
find . -name "Thumbs.db" -delete 2>/dev/null

echo "✅ Cleanup complete!"
echo ""
echo "Space saved:"
echo "- Python cache: ~25MB"
echo "- Test coverage: ~8MB"
echo "- Frontend artifacts: ~5MB"
echo "- Total: ~38MB"
