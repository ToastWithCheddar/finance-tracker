#!/bin/bash

# Test script
echo "🧪 Running Finance Tracker Tests..."

# Run backend tests
echo "🐍 Running backend tests..."
docker-compose exec backend python -m pytest -v

# Run frontend tests (when implemented)
# echo "⚛️  Running frontend tests..."
# docker-compose exec frontend npm test

echo "✅ Tests completed!"