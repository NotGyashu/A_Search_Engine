# 🔍 AI Search Engine - Backend Architecture Documentation

## 📋 Overview

This document describes the **clean, modular backend architecture** for the AI Search Engine, with **clear separation between frontend and backend responsibilities**.

## 🏗️ Architecture Principles

### 1. **Clean Separation of Concerns**
- **Backend**: Pure API server, no frontend code
- **Frontend**: React app, pure UI/UX
- **Communication**: RESTful JSON APIs

### 2. **Modular Design**
- **Core Services**: Business logic (Search, Database, AI)
- **API Layer**: HTTP endpoints and validation
- **Utils**: Helper functions and utilities

### 3. **Dependency Injection**
- Services are injected into API routes
- Easy testing and mocking
- Clean service boundaries

## 📁 Directory Structure

```
backend/
├── core/                      # 🧠 BUSINESS LOGIC
│   ├── __init__.py
│   ├── database_service.py    # Database operations
│   ├── search_service.py      # BM25 search engine
│   └── ai_service.py          # AI summarization
├── api/                       # 🌐 API LAYER
│   ├── __init__.py
│   ├── server.py             # FastAPI application
│   ├── routes.py             # API endpoints
│   └── models.py             # Pydantic models
├── utils/                     # 🔧 UTILITIES
│   ├── __init__.py
│   └── helpers.py            # Helper functions
├── legacy_files/             # 🗂️ OLD FILES (archived)
├── main.py                   # 🚀 ENTRY POINT
└── requirements.txt          # 📦 DEPENDENCIES
```

## 🔄 Data Flow

### Search Request Flow
```
Frontend (React) → Backend API → Search Service → Database Service → Response
     ↓                                   ↓
  User Input                        BM25 Algorithm
     ↓                                   ↓
  JSON Request                     AI Enhancement
     ↓                                   ↓
  HTTP POST                        JSON Response
```

### Detailed Flow
1. **User Input**: User types query in React frontend
2. **API Request**: Frontend sends POST to `/api/search`
3. **Validation**: Pydantic validates request data
4. **Search Service**: BM25 algorithm processes query
5. **Database Service**: Retrieves relevant documents
6. **AI Service**: Generates intelligent summary
7. **Response**: JSON response sent back to frontend
8. **UI Update**: React displays results

## 🛠️ Core Services

### 1. Database Service (`core/database_service.py`)

**Purpose**: Handle all database operations

**Key Features**:
- Connection management with context managers
- Document retrieval and statistics
- Health checks and error handling
- Batch operations for performance

**Main Methods**:
```python
get_all_documents() -> List[Dict]
get_document_by_id(doc_id: int) -> Optional[Dict]
get_database_stats() -> Dict
health_check() -> Dict
```

**Example Usage**:
```python
db_service = DatabaseService()
documents = db_service.get_all_documents()
stats = db_service.get_database_stats()
```

### 2. Search Service (`core/search_service.py`)

**Purpose**: BM25 search algorithm implementation

**Key Features**:
- Advanced BM25 relevance ranking
- Intelligent tokenization and indexing
- Query processing and result formatting
- Performance optimization

**Main Methods**:
```python
search(query: str, limit: int) -> Dict
rebuild_index() -> Dict
get_stats() -> Dict
health_check() -> Dict
```

**BM25 Algorithm**:
- **K1**: Term frequency saturation (default: 1.5)
- **B**: Document length normalization (default: 0.75)
- **IDF**: Inverse Document Frequency calculation
- **Title Weighting**: Titles get extra weight in indexing

**Example Usage**:
```python
search_service = SearchService(db_service)
results = search_service.search("python programming", limit=10)
```

### 3. AI Service (`core/ai_service.py`)

**Purpose**: AI-powered summarization and enhancement

**Key Features**:
- Multiple AI model support (OpenAI, HuggingFace, Ollama)
- Intelligent fallback system
- Smart template-based summarization (no downloads)
- Context-aware summary generation

**Supported Models**:
- **Smart Template**: Default, no external dependencies
- **OpenAI GPT**: Cloud-based, requires API key
- **HuggingFace Transformers**: Local models
- **Ollama**: Local LLM server

**Main Methods**:
```python
generate_summary(query: str, results: List[Dict]) -> Dict
get_stats() -> Dict
health_check() -> Dict
```

**Example Usage**:
```python
ai_service = AIService()
summary = ai_service.generate_summary("machine learning", search_results)
```

## 🌐 API Layer

### 1. Server (`api/server.py`)

**Purpose**: FastAPI application configuration

**Key Features**:
- CORS middleware for frontend integration
- Request logging and error handling
- Custom exception handlers
- Health monitoring

**Configuration**:
```python
app = FastAPI(
    title="AI Search Engine API",
    version="3.0.0",
    docs_url="/api/docs"
)
```

### 2. Routes (`api/routes.py`)

**Purpose**: API endpoint definitions

**Available Endpoints**:

#### `POST /api/search`
- **Purpose**: Main search endpoint
- **Input**: `SearchRequest` (query, limit, include_ai_summary)
- **Output**: `SearchResponse` (results, AI summary, metrics)
- **Example**:
```json
{
  "query": "machine learning",
  "limit": 10,
  "include_ai_summary": true
}
```

#### `GET /api/search`
- **Purpose**: Simple search with query parameters
- **Parameters**: `q`, `limit`, `ai_summary`
- **Example**: `/api/search?q=python&limit=5&ai_summary=true`

#### `GET /api/stats`
- **Purpose**: System statistics
- **Output**: Database, search, and AI service statistics

#### `GET /api/health`
- **Purpose**: Health check for all services
- **Output**: Service status and diagnostics

#### `GET /api/config`
- **Purpose**: Current system configuration
- **Output**: Search, AI, and server settings

#### `POST /api/search/rebuild`
- **Purpose**: Rebuild search index (admin endpoint)
- **Output**: Rebuild status and new statistics

### 3. Models (`api/models.py`)

**Purpose**: Pydantic models for request/response validation

**Key Models**:
- `SearchRequest`: Input validation
- `SearchResponse`: Output formatting
- `StatsResponse`: Statistics formatting
- `HealthCheck`: Health status
- `ErrorResponse`: Error handling

## 🔧 Utilities

### Helper Functions (`utils/helpers.py`)

**Purpose**: Common utility functions

**Key Classes**:
- `ResponseFormatter`: Consistent API responses
- `QueryProcessor`: Query validation and cleaning
- `ResultProcessor`: Result formatting and highlighting
- `PerformanceTracker`: Performance monitoring

## 🚀 Running the Backend

### 1. Installation
```bash
cd ai_search/backend
pip install -r requirements.txt
```

### 2. Start Server
```bash
python main.py
```

### 3. Access Points
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/health

## 📊 Frontend Integration

### 1. Proxy Configuration
Frontend `package.json` includes:
```json
{
  "proxy": "http://localhost:8000"
}
```

### 2. API Calls
Frontend makes requests to `/api/search`, `/api/stats`, etc.

### 3. Error Handling
Backend returns standardized error responses:
```json
{
  "status": "error",
  "message": "Error description",
  "error_code": "ERROR_TYPE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🔍 Search Flow Example

### 1. User Action
```javascript
// Frontend: User types "python programming"
const searchQuery = "python programming";
```

### 2. API Request
```javascript
// Frontend: Send POST request
fetch('/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: searchQuery,
    limit: 10,
    include_ai_summary: true
  })
})
```

### 3. Backend Processing
```python
# Backend: Process request
search_result = search_service.search(query="python programming", limit=10)
ai_summary = ai_service.generate_summary(query, search_result['results'])
```

### 4. Response
```json
{
  "query": "python programming",
  "results": [
    {
      "id": 1,
      "url": "https://example.com/python-guide",
      "title": "Python Programming Guide",
      "content_preview": "Learn Python programming...",
      "domain": "example.com",
      "word_count": 2500,
      "relevance_score": 15.432
    }
  ],
  "total_found": 1,
  "search_time_ms": 12.5,
  "ai_summary": "Python programming resources including tutorials and guides...",
  "ai_model_used": "smart_template",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 5. Frontend Display
```javascript
// Frontend: Display results
setResults(responseData);
```

## 📈 Performance Considerations

### 1. Search Performance
- **Index Loading**: Built once on startup
- **Query Processing**: Sub-millisecond BM25 calculations
- **Result Caching**: In-memory caching for repeated queries

### 2. Database Performance
- **Connection Pooling**: Efficient connection management
- **Batch Operations**: Optimized database queries
- **Indexing**: Strategic database indexes

### 3. AI Performance
- **Model Fallback**: Graceful degradation
- **Context Optimization**: Efficient context preparation
- **Caching**: Template-based caching for common queries

## 🧪 Testing

### 1. Manual Testing
```bash
# Health check
curl http://localhost:8000/api/health

# Search test
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'

# Stats
curl http://localhost:8000/api/stats
```

### 2. Automated Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## 🔧 Configuration

### Environment Variables
```bash
# Optional: OpenAI API key
export OPENAI_API_KEY="your-key-here"

# Optional: Custom database path
export DATABASE_PATH="/custom/path/to/database.db"

# Optional: Debug mode
export DEBUG_MODE=true
```

### Configuration Files
- `common/config.py`: All configuration options
- `backend/requirements.txt`: Dependencies
- `frontend/package.json`: Frontend proxy settings

## 🚨 Error Handling

### 1. Service Errors
- Database connection failures
- Search index corruption
- AI model unavailability

### 2. API Errors
- Request validation failures
- Rate limiting
- Internal server errors

### 3. Client Errors
- Network timeouts
- Invalid requests
- Authentication failures

## 🔐 Security Considerations

### 1. Input Validation
- Pydantic models validate all inputs
- Query length limits
- SQL injection prevention

### 2. CORS Configuration
- Configured for frontend origin
- Credential handling
- Method restrictions

### 3. Error Information
- Sanitized error messages
- No sensitive data exposure
- Proper logging

## 📚 Development Guidelines

### 1. Code Style
- Follow PEP 8 for Python
- Use type hints
- Document all functions

### 2. Service Architecture
- Keep services focused and single-purpose
- Use dependency injection
- Implement proper error handling

### 3. API Design
- RESTful principles
- Consistent response formats
- Proper HTTP status codes

## 🔄 Deployment

### 1. Development
```bash
python main.py
```

### 2. Production
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.server:app
```

### 3. Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

**✅ The backend is now clean, modular, and completely separated from the frontend!**

**🔗 Clear API boundaries enable independent development of frontend and backend components.**

**📖 Full API documentation available at: http://localhost:8000/api/docs**
