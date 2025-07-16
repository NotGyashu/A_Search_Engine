#!/bin/bash

# AI Search Engine - Complete Startup Script
# This script starts both backend and frontend services

echo "🚀 AI Search Engine - Starting Services..."
echo "=========================================="

# Check if we're in the right directory
if [ ! -d "ai_search" ]; then
    echo "❌ Error: Please run this script from the mini_search_engine directory"
    exit 1
fi

# Check if database exists
if [ ! -f "ai_search/backend/data/processed/documents.db" ]; then
    echo "⚠️  Warning: Database not found. You may need to run the data pipeline first."
    echo "   To process data: cd ai_search/data_pipeline && python processor.py"
fi

# Function to start backend
start_backend() {
    echo "🔧 Starting Backend Server..."
    cd ai_search/backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
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

# Check command line arguments
case "$1" in
    "backend")
        start_backend
        ;;
    "frontend")
        start_frontend
        ;;
    "both"|"")
        echo "🚀 Starting both backend and frontend services..."
        echo "   Use 'Ctrl+C' to stop services"
        echo ""
        
        # Start backend in background
        (start_backend) &
        BACKEND_PID=$!
        
        # Wait a moment for backend to start
        sleep 3
        
        # Start frontend in background
        (start_frontend) &
        FRONTEND_PID=$!
        
        # Wait for both processes
        wait $BACKEND_PID $FRONTEND_PID
        ;;
    *)
        echo "Usage: $0 [backend|frontend|both]"
        echo ""
        echo "Options:"
        echo "  backend   - Start only the backend server"
        echo "  frontend  - Start only the frontend server"
        echo "  both      - Start both services (default)"
        echo ""
        echo "Access URLs:"
        echo "  Frontend: http://localhost:3000"
        echo "  Backend:  http://localhost:8000"
        echo "  API Docs: http://localhost:8000/api/docs"
        exit 1
        ;;
esac
