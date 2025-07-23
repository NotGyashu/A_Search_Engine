# 🚀 Zero-Cost Deployment Guide for AI Search Engine

## 🏗️ Architecture Overview

Your search engine consists of 4 main components:

1. **C++ Crawler** - Data collection (runs daily/weekly)
2. **React Frontend** - User interface and search interface
3. **FastAPI Backend** - Search API and WebSocket handling
4. **AI Runner Service** - AI summarization microservice

## 💰 Zero-Cost Deployment Strategy

### Option 1: Recommended - Vercel + Railway + GitHub Actions

#### 🎨 Frontend Deployment (Vercel)
- **Platform**: Vercel (Free tier)
- **Features**: 100 GB bandwidth, unlimited personal projects
- **Perfect for**: React apps with automatic deployments

#### 🔧 Backend Services (Railway)
- **Platform**: Railway (Free tier)
- **Features**: $5 credit monthly, 500 hours
- **Deploy**: Both FastAPI Backend and AI Runner

#### 🤖 Crawler (GitHub Actions)
- **Platform**: GitHub Actions (Free tier)
- **Features**: 2000 minutes/month
- **Perfect for**: Scheduled data collection

---

## 📋 Step-by-Step Deployment

### 1. Prepare Your Repository

```bash
# Create deployment configurations
mkdir deployment
cd deployment
```

### 2. Frontend Deployment (Vercel)

#### Create Vercel Configuration
```json
{
  "name": "nebula-search-frontend",
  "version": 2,
  "builds": [
    {
      "src": "ai_search/frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "build"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/ai_search/frontend/$1"
    }
  ],
  "env": {
    "REACT_APP_BACKEND_URL": "your-backend-url.up.railway.app"
  }
}
```

#### Deploy Steps:
1. Push code to GitHub
2. Connect Vercel to your GitHub repo
3. Set root directory to `ai_search/frontend`
4. Deploy automatically on push

### 3. Backend Services (Railway)

#### Create railway.toml for Backend
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "cd ai_search/backend && python main.py"
healthcheckPath = "/api/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[env]
PORT = "8000"
BACKEND_HOST = "0.0.0.0"
DATABASE_PATH = "./data/processed/documents.db"
```

#### Create railway.toml for AI Runner
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "cd ai_search/ai_runner && python app.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"

[env]
PORT = "8001"
GOOGLE_API_KEY = "${{secrets.GOOGLE_API_KEY}}"
```

### 4. Crawler Deployment (GitHub Actions)

#### Create .github/workflows/crawler.yml
```yaml
name: Daily Data Crawling

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  crawl-data:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup C++ Environment
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake build-essential
        
    - name: Build Crawler
      run: |
        cd crawler
        mkdir -p build
        cd build
        cmake ..
        make
        
    - name: Run Crawler
      run: |
        cd crawler/build
        ./web_crawler --max-pages 1000 --output ../data/
        
    - name: Process Data
      run: |
        cd ai_search/data_pipeline
        python process_crawled_data.py
        
    - name: Upload Database
      uses: actions/upload-artifact@v3
      with:
        name: search-database
        path: ai_search/backend/data/processed/documents.db
        
    - name: Deploy to Railway
      env:
        RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      run: |
        # Push updated database to Railway
        railway up --service backend
```

---

## 🔧 Alternative Free Hosting Options

### Option 2: All-in-One Solutions

#### A. Render.com (Free Tier)
```yaml
# render.yaml
services:
  - type: web
    name: nebula-frontend
    env: static
    buildCommand: cd ai_search/frontend && npm run build
    staticPublishPath: ai_search/frontend/build
    
  - type: web
    name: nebula-backend
    env: python
    buildCommand: cd ai_search/backend && pip install -r requirements.txt
    startCommand: cd ai_search/backend && python main.py
    
  - type: web
    name: nebula-ai-runner
    env: python
    buildCommand: cd ai_search/ai_runner && pip install -r requirements.txt
    startCommand: cd ai_search/ai_runner && python app.py
```

#### B. Heroku (Free tier discontinued, but alternatives exist)

#### C. Google Cloud Run (Free tier)
```dockerfile
# Dockerfile.backend
FROM python:3.11-slim
WORKDIR /app
COPY ai_search/backend/requirements.txt .
RUN pip install -r requirements.txt
COPY ai_search/backend/ .
COPY ai_search/common/ ./common/
CMD ["python", "main.py"]
```

### Option 3: Self-Hosted (VPS)

#### Free VPS Options:
1. **Oracle Cloud Free Tier** - 2 VMs forever free
2. **Google Cloud Free Tier** - $300 credit + always free
3. **AWS Free Tier** - 12 months free
4. **Azure Free Tier** - $200 credit

---

## 📦 Docker Deployment Configuration

### Create docker-compose.yml
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: ai_search/frontend/Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build:
      context: .
      dockerfile: ai_search/backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_PATH=/app/data/documents.db
      - AI_RUNNER_URL=http://ai-runner:8001
    volumes:
      - ./data:/app/data
    depends_on:
      - ai-runner

  ai-runner:
    build:
      context: .
      dockerfile: ai_search/ai_runner/Dockerfile
    ports:
      - "8001:8001"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}

  crawler:
    build:
      context: .
      dockerfile: crawler/Dockerfile
    volumes:
      - ./data:/app/data
    profiles:
      - crawler  # Only run manually
```

---

## 🚀 Recommended Deployment Steps

### Phase 1: Quick Start (Recommended)

1. **Deploy Frontend to Vercel**
   ```bash
   cd ai_search/frontend
   npm run build
   # Connect to Vercel
   ```

2. **Deploy Backend to Railway**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   railway login
   railway init
   railway up
   ```

3. **Setup Crawler on GitHub Actions**
   - Add secrets: GOOGLE_API_KEY, RAILWAY_TOKEN
   - Configure workflow

### Phase 2: Production Ready

1. **Add Database Persistence**
   - Use Railway Volume for SQLite
   - Or migrate to PostgreSQL

2. **Add Monitoring**
   - Uptime monitoring
   - Error tracking
   - Performance metrics

3. **Optimize Costs**
   - Use CDN for static assets
   - Implement caching
   - Optimize database queries

---

## 💡 Cost Optimization Tips

### 1. Resource Management
- **Frontend**: Static hosting (Vercel/Netlify)
- **Backend**: Serverless or container (Railway/Render)
- **Database**: SQLite for small scale, PostgreSQL for growth
- **AI**: Efficient model usage, caching summaries

### 2. Free Tier Maximization
- **Vercel**: Unlimited bandwidth for personal projects
- **Railway**: $5 monthly credit
- **GitHub Actions**: 2000 minutes/month
- **Google AI**: Free tier available

### 3. Performance Optimization
```python
# ai_search/backend/api/routes.py
# Add caching for expensive operations
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_search_results(query: str, limit: int):
    # Cache search results
    pass

# Add response compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 🔐 Security & Environment Variables

### Required Environment Variables
```bash
# Frontend
REACT_APP_BACKEND_URL=https://your-backend.railway.app

# Backend
DATABASE_PATH=/app/data/documents.db
AI_RUNNER_URL=http://ai-runner:8001
CORS_ORIGINS=https://your-frontend.vercel.app

# AI Runner
GOOGLE_API_KEY=your_google_api_key
PORT=8001

# Crawler (GitHub Actions)
RAILWAY_TOKEN=your_railway_token
GOOGLE_API_KEY=your_google_api_key
```

---

## 📊 Monitoring & Analytics

### Free Monitoring Tools
1. **UptimeRobot** - Service monitoring
2. **Google Analytics** - Frontend analytics
3. **Sentry** - Error tracking (free tier)
4. **Railway Metrics** - Built-in monitoring

### Health Check Endpoints
```python
# Add to your backend
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "database": "connected",
        "ai_service": "available"
    }
```

---

## 🎯 Next Steps

1. **Choose your deployment platform** (Recommended: Vercel + Railway)
2. **Set up CI/CD pipeline** with GitHub Actions
3. **Configure environment variables** and secrets
4. **Test the deployment** end-to-end
5. **Set up monitoring** and alerts
6. **Optimize for production** (caching, compression, etc.)

This setup will give you a production-ready, scalable search engine with zero hosting costs for normal usage levels! 🚀
