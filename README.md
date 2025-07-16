    # Mini Search Engine - AI-Powered Document Search

    A **modern, modular, and high-performance search engine** that combines advanced BM25 ranking with intelligent AI summarization. Built with clean architecture and production-ready components.

    ## 🚀 Quick Start

    ```bash
    # Clone and navigate to the AI search directory
    cd mini_search_engine/ai_search

    # Backend Setup
    cd backend
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt

    # Process Data (first time only)
    cd ../data_pipeline
    python processor.py

    # Start Backend
    cd ../backend
    python api_server.py

    # Frontend Setup (in a new terminal)
    cd ../frontend
    npm install
    npm start
    ```

    **🎯 Access the application at:**
    - **Frontend**: http://localhost:3000
    - **API**: http://localhost:8000
    - **Health Check**: http://localhost:8000/health

    ## 📁 Project Structure

    ```
    mini_search_engine/
    ├── ai_search/                    # 🎯 MAIN APPLICATION
    │   ├── backend/                  # Python FastAPI backend
    │   │   ├── api_server.py        # REST API server
    │   │   ├── search_engine.py     # BM25 + AI search engine
    │   │   ├── requirements.txt     # Python dependencies
    │   │   └── data/               # Processed database
    │   ├── frontend/                # React web interface
    │   │   ├── src/                # React components
    │   │   ├── public/             # Static files
    │   │   └── package.json        # Node.js dependencies
    │   ├── data_pipeline/           # Data processing
    │   │   └── processor.py        # ETL pipeline
    │   ├── common/                  # Shared utilities
    │   │   ├── config.py           # Configuration management
    │   │   └── utils.py            # Shared utilities
    │   └── docs/                    # 📚 COMPLETE DOCUMENTATION
    │       └── README.md           # Detailed documentation
    ├── RawHTMLdata/                 # Raw HTML data files
    ├── crawler/                     # C++ web crawler
    ├── legacy_backup/               # Archived legacy files
    └── README.md                    # This file
    ```

    ## ✨ Features

    ### 🔍 **Ultra-Fast Search**
    - **BM25 Algorithm**: Advanced relevance ranking
    - **Sub-millisecond Performance**: 3-20ms search response
    - **22,000+ Documents**: Full-text indexed and searchable
    - **Smart Query Processing**: Tokenization and normalization

    ### 🧠 **AI-Enhanced Results**
    - **Intelligent Summarization**: Context-aware summaries
    - **Multiple AI Models**: OpenAI, HuggingFace, Local models
    - **Smart Templates**: No-download AI alternative
    - **Fallback System**: Graceful degradation

    ### 🏗️ **Modern Architecture**
    - **Modular Design**: Clean separation of concerns
    - **RESTful API**: Comprehensive endpoints
    - **React Frontend**: Modern, responsive interface
    - **Centralized Config**: Single configuration source

    ### 📊 **Production Ready**
    - **Error Handling**: Comprehensive error management
    - **Logging**: Detailed application logging
    - **Health Monitoring**: System status endpoints
    - **Performance Tracking**: Built-in metrics

    ## 🛠️ Technology Stack

    | Component | Technology | Purpose |
    |-----------|------------|---------|
    | **Backend** | Python + FastAPI + SQLite | REST API and search engine |
    | **Frontend** | React + Modern CSS | User interface |
    | **Search** | BM25 Algorithm + TF-IDF | Document ranking |
    | **AI** | OpenAI/HuggingFace/Ollama | Smart summarization |
    | **Database** | SQLite + Full-text indexing | Document storage |
    | **Data Pipeline** | Python + Batch processing | ETL and cleaning |

    ## 📊 Performance Metrics

    - **🚀 Search Speed**: 3-20ms per query
    - **📈 Throughput**: 1000+ searches/minute  
    - **💾 Memory Usage**: ~500MB for full index
    - **🗄️ Database Size**: 487MB SQLite
    - **📄 Document Count**: 22,833 indexed documents
    - **🔤 Term Count**: 582,713 unique terms

    ## 🎯 API Examples

    ### Search with AI Summary
    ```bash
    curl -X POST http://localhost:8000/api/search \
    -H "Content-Type: application/json" \
    -d '{
        "query": "machine learning algorithms",
        "limit": 10,
        "include_ai_summary": true
    }'
    ```

    ### Quick Search
    ```bash
    curl "http://localhost:8000/api/search?q=python+programming&limit=5"
    ```

    ### System Health
    ```bash
    curl http://localhost:8000/health
    ```

    ## 📚 Documentation

    **📖 For complete documentation, see:** [`ai_search/docs/README.md`](ai_search/docs/README.md)

    The comprehensive documentation includes:
    - 🏗️ **Architecture Details**: Component interaction and data flow
    - 🔧 **Installation Guide**: Step-by-step setup instructions
    - 📡 **API Reference**: Complete endpoint documentation
    - ⚙️ **Configuration**: All configuration options
    - 🛠️ **Development**: Development workflow and testing
    - 🚀 **Deployment**: Production deployment guide
    - ⚡ **Performance**: Optimization and benchmarking
    - 🔧 **Troubleshooting**: Common issues and solutions

    ## 🧩 Components Overview

    ### Backend (`ai_search/backend/`)
    - **api_server.py**: FastAPI REST API with health monitoring
    - **search_engine.py**: BM25 search algorithm with AI enhancement
    - **requirements.txt**: Python dependencies (FastAPI, SQLite, optional AI)

    ### Frontend (`ai_search/frontend/`)
    - **React Application**: Modern, responsive search interface
    - **Components**: SearchBox, Results, Features, API documentation
    - **Responsive Design**: Mobile and desktop optimized

    ### Data Pipeline (`ai_search/data_pipeline/`)
    - **processor.py**: ETL pipeline for raw HTML data
    - **Features**: Cleaning, deduplication, validation, batch processing

    ### Common (`ai_search/common/`)
    - **config.py**: Centralized configuration management
    - **utils.py**: Shared utilities and helper functions

    ## 🔄 Development Workflow

    ### 1. Backend Development
    ```bash
    cd ai_search/backend
    source venv/bin/activate
    python api_server.py  # Start with auto-reload
    ```

    ### 2. Frontend Development
    ```bash
    cd ai_search/frontend
    npm start  # Start development server
    ```

    ### 3. Data Processing
    ```bash
    cd ai_search/data_pipeline
    python processor.py  # Process raw data
    ```

    ## 🎨 Key Features in Detail

    ### Advanced Search Engine
    - **BM25 Algorithm**: Industry-standard relevance ranking
    - **Full-text Indexing**: Efficient document retrieval
    - **Smart Tokenization**: Handles various text formats
    - **Performance Optimized**: Sub-millisecond search times

    ### AI-Powered Summarization
    - **Smart Templates**: Default summarization without downloads
    - **OpenAI Integration**: Cloud-based GPT models
    - **Local Models**: HuggingFace Transformers and Ollama
    - **Fallback System**: Graceful degradation when AI unavailable

    ### Modern Web Interface
    - **React Components**: Modular, reusable interface
    - **Responsive Design**: Works on mobile and desktop
    - **Real-time Search**: Instant results as you type
    - **API Documentation**: Built-in API explorer

    ## 🔧 Configuration

    All configuration is centralized in `ai_search/common/config.py`:

    ```python
    # Server Configuration
    BACKEND_PORT = 8000
    FRONTEND_PORT = 3000

    # Search Engine
    BM25_K1 = 1.5  # Term frequency saturation
    BM25_B = 0.75  # Document length normalization

    # AI Models
    AI_MODEL_PREFERENCE = [
        "smart_template",  # Default: no downloads required
        "openai_gpt",      # Requires OPENAI_API_KEY
        "ollama",          # Local models
        "transformers"     # HuggingFace models
    ]
    ```

    ## 🚀 Deployment

    ### Development
    ```bash
    # Backend
    cd ai_search/backend && python api_server.py

    # Frontend
    cd ai_search/frontend && npm start
    ```

    ### Production
    ```bash
    # Backend with Gunicorn
    pip install gunicorn
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_server:app

    # Frontend build
    cd ai_search/frontend && npm run build
    ```

    ## 🏆 Project Highlights

    ### ✅ **Complete Modularization**
    - All AI search functionality moved to `ai_search/` directory
    - Clean separation: Backend, Frontend, Data Pipeline, Common utilities
    - Legacy files archived in `legacy_backup/`

    ### ✅ **Production-Ready Architecture**
    - RESTful API with comprehensive error handling
    - Modern React frontend with responsive design
    - Centralized configuration and logging
    - Health monitoring and performance tracking

    ### ✅ **High Performance**
    - BM25 algorithm for accurate relevance ranking
    - Optimized database queries with full-text indexing
    - Efficient batch processing for large datasets
    - Sub-millisecond search response times

    ### ✅ **AI Integration**
    - Multiple AI model support with fallback system
    - Smart template-based summarization as default
    - Cloud and local model integration options
    - Intelligent context-aware summaries

    ## 🤝 Contributing

    1. **Read the documentation**: [`ai_search/docs/README.md`](ai_search/docs/README.md)
    2. **Set up development environment**: Follow quick start guide
    3. **Make changes**: Follow modular architecture principles
    4. **Test thoroughly**: Both backend and frontend components
    5. **Update documentation**: Keep docs current

    ## 📝 License

    This project is designed for educational and research purposes. See individual component licenses for details.

    ---

    **🎯 Ready to search intelligently? Start with the [Quick Start](#-quick-start) guide!**

    **📚 Need more details? Check the [Complete Documentation](ai_search/docs/README.md)**
