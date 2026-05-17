#!/bin/bash
# Brand Intel - Start all services

echo "========================================="
echo "  Brand Intel - Starting Services"
echo "========================================="

# Activate virtual environment
VENV_DIR="$(pwd)/.venv"
export PATH="$VENV_DIR/bin:$PATH"

# Load MONGODB_URI from .env if exists
if [ -f backend/.env ]; then
    export $(grep -v '^#' backend/.env | xargs) 2>/dev/null
fi

MONGO_URI="${MONGODB_URI:-mongodb://localhost:27017}"

# Try to connect to MongoDB using the configured URI
echo "Checking MongoDB connection..."

MONGO_CHECK=$(python3 << 'PYEOF'
import sys, os
from pymongo import MongoClient
uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
PYEOF
)

if [[ "$MONGO_CHECK" == "OK" ]]; then
    echo "MongoDB: Connected"
else
    echo "WARNING: $MONGO_CHECK"
    echo "Please check your MONGODB_URI in backend/.env"
    exit 1
fi

# Check if .env exists in backend
if [ ! -f backend/.env ]; then
    echo "WARNING: backend/.env not found. Copying from .env.example..."
    cp backend/.env.example backend/.env
    echo "Please edit backend/.env with your API keys before running."
    exit 1
fi

# Start FastAPI server
echo ""
echo "Starting FastAPI server on port 8000..."
cd backend
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!
cd ..

# Wait for API to start
sleep 3

# Start React frontend
echo ""
echo "Starting React frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  Services Started"
echo "========================================="
echo "  API:       http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================="

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $API_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
