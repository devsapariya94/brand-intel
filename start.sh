#!/bin/bash
# Brand Intel - Start all services

echo "========================================="
echo "  Brand Intel - Starting Services"
echo "========================================="

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null; then
    echo "WARNING: MongoDB is not running. Please start it first."
    echo "  brew services start mongodb-community  (macOS)"
    echo "  sudo systemctl start mongod            (Linux)"
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

# Start Streamlit frontend
echo ""
echo "Starting Streamlit frontend on port 8501..."
cd frontend
streamlit run app.py --server.port 8501 --server.headless true &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  Services Started"
echo "========================================="
echo "  API:       http://localhost:8000"
echo "  Frontend:  http://localhost:8501"
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
