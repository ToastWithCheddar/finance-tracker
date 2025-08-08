#!/bin/bash

# Development startup script
echo "🚀 Starting Finance Tracker Development Environment..."
echo "📍 Mode: DEVELOPMENT ONLY (not for production)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Development .env created with safe defaults"
    echo "💡 You can edit .env to customize your development setup"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check for UI-only mode
if [ "$1" = "ui-only" ] || [ "$1" = "ui" ]; then
    echo "🎭 Starting UI-only mode (frontend with mock data)..."
    docker-compose -f docker-compose.ui-only.yml up --build -d
    echo "✅ UI-only mode started!"
    echo "📱 Frontend: http://localhost:3000 (with mock data)"
    echo "🎭 Mock backend: http://localhost:8000 (optional)"
    echo "💡 To start with mock backend: docker-compose -f docker-compose.ui-only.yml --profile with-backend up -d"
    exit 0
fi

# Start development environment
echo "🐳 Starting Docker containers in development mode..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

# Check if database needs to be reset
echo "🗄️  Setting up database..."
# Mark current schema as up to date with Alembic (in case tables exist)
docker-compose exec backend alembic stamp head 2>/dev/null || true
# Run any pending migrations
docker-compose exec backend alembic upgrade head

# Seed default data
echo "🌱 Seeding default data..."
docker-compose exec backend python -m app.scripts.seed_data

echo "✅ Development environment ready!"
echo ""
echo "📋 Available services:"
echo "   📱 Frontend: http://localhost:3000 (with hot reload)"
echo "   🔧 Backend API: http://localhost:8000 (with auto-reload)"
echo "   📚 API Documentation: http://localhost:8000/docs"
echo "   🗄️  Database: localhost:5432 (finance_tracker_dev)"
echo "   📦 Redis: localhost:6379"
echo "   🤖 ML Worker: localhost:8001"
echo ""
echo "🔧 Development commands:"
echo "   Stop all: docker-compose down"
echo "   View logs: docker-compose logs -f [service]"
echo "   Shell access: docker-compose exec [service] bash"
echo "   Restart service: docker-compose restart [service]"
echo "   Fresh start: docker-compose down -v && ./scripts/dev.sh"
echo "   UI-only mode: ./scripts/dev.sh ui-only"
echo ""
echo "🎭 Development Modes:"
echo "   Full: All services (database, redis, ML worker)"
echo "   UI-only: Frontend with mock data (no database)"
echo ""
echo "⚠️  Remember: This is a DEVELOPMENT setup only!"