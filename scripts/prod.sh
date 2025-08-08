#!/bin/bash

# Production startup script
echo "Starting Finance Tracker Production Environment..."

# Build and start production containers
docker-compose up --build -d

# Wait for services
sleep 15

# Check health
docker-compose ps

echo "Production environment ready!"
echo "Application: http://localhost"