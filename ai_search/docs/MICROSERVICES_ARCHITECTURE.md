# 🚀 AI Search Engine - Microservices Architecture

## 🎯 Overview

This project now uses a **microservices architecture** to handle the dependency conflict between FastAPI and Google Cloud AI. The system is split into two services:

1. **Backend Service** (Port 8000) - Pure FastAPI with search functionality
2. **AI Runner Service** (Port 8001) - Dedicated AI microservice with Google Gemini support

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Frontend      │    │   Backend       │    │   AI Runner     │
│   (React)       │    │   (FastAPI)     │    │   (FastAPI)     │
│   Port 3000     │    │   Port 8000     │    │   Port 8001     │
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ HTTP API calls       │ HTTP API calls       │
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                        ┌────────▼────────┐
                        │                 │
                        │   SQLite DB     │
                        │   (Documents)   │
                        │                 │
                        └─────────────────┘
```

## 🔧 Services Breakdown

### 🔍 Backend Service (Port 8000)
- **Pure FastAPI** with minimal dependencies
- **BM25 Search Engine** with enhanced ranking
- **SQLite Database** operations
- **Domain-based ranking** and content filtering
- **Health monitoring** and stats
- **API Documentation** at `/docs`

**Key Files:**
- `backend/main.py` - Entry point
- `backend/api/routes.py` - API endpoints
- `backend/core/search_service.py` - Search logic
- `backend/core/ai_client_service.py` - AI Runner client

### 🤖 AI Runner Service (Port 8001)
- **Dedicated AI environment** with Google Cloud dependencies
- **Multiple AI models**: Google Gemini, OpenAI, Transformers
- **Intelligent fallback** system
- **Independent scaling** and deployment
- **Fault isolation** from main backend

**Key Files:**
- `ai_runner/app.py` - AI microservice entry point
- `ai_runner/ai_service.py` - AI logic and model handling
- `ai_runner/requirements.txt` - AI-specific dependencies

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python 3.8+
# Install Node.js 16+ (for frontend)
# Get Google API key for Gemini
```

### 1. Setup AI Runner
```bash
cd ai_search/ai_runner

# Create virtual environment
python -m venv venv-ai
source venv-ai/bin/activate  # On Windows: venv-ai\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env and add your GOOGLE_API_KEY
```

### 2. Setup Backend
```bash
cd ai_search/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start All Services
```bash
# Option 1: Use the startup script
cd ai_search
./start_all_services.sh

# Option 2: Start individually
# Terminal 1: AI Runner
cd ai_search/ai_runner
source venv-ai/bin/activate
python app.py

# Terminal 2: Backend
cd ai_search/backend
source venv/bin/activate
python main.py

# Terminal 3: Frontend
cd ai_search/frontend
npm install
npm start
```

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | React web interface |
| **Backend API** | http://localhost:8000 | Main search API |
| **Backend Docs** | http://localhost:8000/api/docs | Swagger documentation |
| **AI Runner** | http://localhost:8001 | AI microservice |
| **AI Runner Docs** | http://localhost:8001/docs | AI API documentation |

## 📡 API Endpoints

### Backend Service (Port 8000)
```bash
GET  /api/health              # Health check
GET  /api/stats               # System statistics
POST /api/search              # Search with AI summary
GET  /api/search?q=query      # GET search endpoint
```

### AI Runner Service (Port 8001)
```bash
GET  /health                  # AI service health
GET  /stats                   # AI model statistics  
POST /summarize               # Generate AI summary
```

## 🔄 Communication Flow

1. **User searches** via Frontend
2. **Frontend calls** Backend API (`/api/search`)
3. **Backend performs** BM25 search on database
4. **Backend calls** AI Runner (`/summarize`) for AI summary
5. **AI Runner** generates summary using available AI models
6. **Backend returns** combined results to Frontend
7. **Frontend displays** search results with AI summary

## 🛠️ Configuration

### Backend Configuration
- **Database**: `backend/data/processed/documents.db`
- **Config**: `common/config.py`
- **Logging**: Structured JSON logs

### AI Runner Configuration
- **Environment**: `ai_runner/.env`
- **Models**: Google Gemini (primary), OpenAI (optional), Transformers (optional)
- **Fallback**: Smart template when AI unavailable

## 🧪 Testing

### Test AI Runner
```bash
cd ai_search/ai_runner
python test_ai_runner.py
```

### Test Backend
```bash
cd ai_search/backend
curl http://localhost:8000/api/health
curl "http://localhost:8000/api/search?q=python&ai_summary=true"
```

## 🎯 Benefits of This Architecture

✅ **Dependency Isolation** - No more package conflicts  
✅ **Independent Scaling** - Scale AI service separately  
✅ **Fault Tolerance** - AI failures don't crash main app  
✅ **Technology Freedom** - Use different tech in each service  
✅ **Development Speed** - Teams can work independently  
✅ **Cost Optimization** - Only run AI service when needed  

## 🔧 Troubleshooting

### AI Runner Issues
```bash
# Check if AI Runner is running
curl http://localhost:8001/health

# Check logs
cd ai_search/ai_runner
python app.py  # See startup logs

# Test with minimal dependencies
# AI Runner falls back to smart templates if models unavailable
```

### Backend Issues
```bash
# Check backend health
curl http://localhost:8000/api/health

# Check database
ls -la ai_search/backend/data/processed/documents.db

# Run without AI (fallback mode)
# Backend works independently of AI Runner
```

### Common Solutions
1. **Port conflicts**: Change ports in config files
2. **Environment issues**: Verify virtual environments are activated
3. **API key issues**: Check `.env` file in ai_runner
4. **Database missing**: Run data pipeline first

## 📚 Development Guide

### Adding New AI Models
1. Edit `ai_runner/ai_service.py`
2. Add model to `_check_available_models()`
3. Implement `_generate_<model>_summary()` method
4. Update requirements.txt if needed

### Adding New Search Features
1. Edit `backend/core/search_service.py`
2. Update API models in `backend/api/models.py`
3. Modify routes in `backend/api/routes.py`

## 🚀 Deployment

### Production Deployment
```bash
# Use Docker for production
# Separate containers for each service
# Use proper load balancer
# Configure monitoring and logging
```

### Environment Variables
```bash
# Backend
DATABASE_PATH=/app/data/documents.db
BACKEND_PORT=8000

# AI Runner  
GOOGLE_API_KEY=your_key_here
AI_RUNNER_PORT=8001
```

This architecture solves your dependency conflict while providing a scalable, maintainable solution! 🎉
