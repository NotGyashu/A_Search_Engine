#!/bin/bash

# AI Search Engine - Complete Startup Script with AI Runner
# This script starts both backend and AI runner microservices

echo "🚀 AI Search Engine - Starting All Services..."
echo "=============================================="

# Check if we're in the right directory
if [ ! -d "ai_search" ]; then
    echo "❌ Error: Please run this script from the mini_search_engine directory"
    exit 1
fi

# Function to start AI Runner
start_ai_runner() {
    echo "🤖 Starting AI Runner Microservice..."
    cd ai_search/ai_runner
    
    # Check if virtual environment exists
    if [ ! -d "venv-ai" ]; then
        echo "❌ Error: AI Runner virtual environment not found!"
        echo "   Please create it first: python -m venv venv-ai"
        exit 1
    fi
    
    # Activate virtual environment
    source venv-ai/bin/activate
    
    # Install dependencies
    echo "📦 Installing AI Runner dependencies..."
    pip install -r requirements.txt
    
    # Start AI Runner server
    echo "🚀 Starting AI Runner on http://localhost:8001"
    python app.py
}

# Function to start backend
start_backend() {
    echo "🔧 Starting Backend Server..."
    cd ai_search/backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "📦 Creating backend virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "📦 Installing backend dependencies..."
    pip install -r requirements.txt
    
    # Start backend server
    echo "🚀 Starting FastAPI server on http://localhost:8000"
    python main.py
}

# Function to start frontend
start_frontend() {
    echo "🎨 Starting Frontend Server..."
    cd ai_search/frontend
    
    # Install dependencies
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        npm install
    fi
    
    # Start frontend server
    echo "🚀 Starting React server on http://localhost:3000"
    npm start
}

# Function to start all services
start_all() {
    echo "🚀 Starting all services in background..."
    echo "   Use 'Ctrl+C' to stop services"
    echo ""
    
    # Start AI Runner in background
    echo "🤖 Starting AI Runner..."
    (start_ai_runner) &
    AI_RUNNER_PID=$!
    
    # Wait for AI Runner to start
    sleep 5
    
    # Start backend in background
    echo "🔧 Starting Backend..."
    (start_backend) &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 3
    
    # Start frontend in background
    echo "🎨 Starting Frontend..."
    (start_frontend) &
    FRONTEND_PID=$!
    
    # Wait for all processes
    wait $AI_RUNNER_PID $BACKEND_PID $FRONTEND_PID
}

# Check command line arguments
case "$1" in
    "ai_runner")
        start_ai_runner
        ;;
    "backend")
        start_backend
        ;;
    "frontend")
        start_frontend
        ;;
    "all"|"")
        start_all
        ;;
    *)
        echo "Usage: $0 [ai_runner|backend|frontend|all]"
        echo ""
        echo "Options:"
        echo "  ai_runner - Start only the AI Runner microservice"
        echo "  backend   - Start only the backend server"
        echo "  frontend  - Start only the frontend server"
        echo "  all       - Start all services (default)"
        echo ""
        echo "Access URLs:"
        echo "  Frontend:   http://localhost:3000"
        echo "  Backend:    http://localhost:8000"
        echo "  AI Runner:  http://localhost:8001"
        echo "  API Docs:   http://localhost:8000/api/docs"
        echo "  AI Docs:    http://localhost:8001/docs"
        exit 1
        ;;
esac
