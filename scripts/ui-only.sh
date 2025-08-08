#!/bin/bash

# UI-only development script
echo "🎭 Starting Finance Tracker UI-Only Mode..."
echo "📍 Mode: UI DEVELOPMENT (frontend with mock data)"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    
    # Set UI-only mode in .env
    echo "" >> .env
    echo "# UI-Only Mode Configuration" >> .env
    echo "USE_MOCK_DATA=true" >> .env
    echo "UI_ONLY_MODE=true" >> .env
    echo "ENABLE_DATABASE=false" >> .env
    echo "ENABLE_REDIS=false" >> .env
    echo "ENABLE_ML_WORKER=false" >> .env
    
    echo "✅ UI-only .env created"
fi

# Check if user wants backend mock API
if [ "$1" = "with-backend" ] || [ "$1" = "backend" ]; then
    echo "🐳 Starting frontend + mock backend..."
    docker-compose -f docker-compose.ui-only.yml --profile with-backend up --build -d
    BACKEND_ENABLED=true
else
    echo "🐳 Starting frontend only (pure mock mode)..."
    docker-compose -f docker-compose.ui-only.yml up --build -d
    BACKEND_ENABLED=false
fi

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to start..."
sleep 5

echo "✅ UI-only mode ready!"
echo ""
echo "📱 Frontend: http://localhost:3000 (with mock data)"
if [ "$BACKEND_ENABLED" = "true" ]; then
    echo "🎭 Mock Backend: http://localhost:8000 (mock API endpoints)"
    echo "📚 Mock API Docs: http://localhost:8000/docs"
else
    echo "💡 Running in pure mock mode (no backend needed)"
fi
echo ""
echo "🎯 UI Development Features:"
echo "   ✅ Hot reload for frontend changes"
echo "   ✅ Mock data for all API calls"
echo "   ✅ No database setup required" 
echo "   ✅ No external API dependencies"
echo "   ✅ Perfect for UI/UX development"
echo ""
echo "🔧 Commands:"
echo "   Stop: docker-compose -f docker-compose.ui-only.yml down"
echo "   Logs: docker-compose -f docker-compose.ui-only.yml logs -f"
echo "   Restart: docker-compose -f docker-compose.ui-only.yml restart"
echo ""
echo "💡 Tips:"
echo "   • Toggle mock mode using the indicator in top-right corner"
echo "   • Use browser dev tools to see mock API calls"
echo "   • All changes to frontend code will auto-reload"
echo "   • No real data will be saved or modified"
echo ""
echo "🎭 Happy UI development!"