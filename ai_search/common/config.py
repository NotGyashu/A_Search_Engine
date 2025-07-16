# AI Search Engine Configuration
# Central configuration file for all AI search components

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# Backend API Server
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
BACKEND_RELOAD = True
BACKEND_LOG_LEVEL = "info"

# Frontend Development Server
FRONTEND_HOST = "localhost"
FRONTEND_PORT = 3000
FRONTEND_PROXY_TARGET = f"http://localhost:{BACKEND_PORT}"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database paths (relative to ai_search root)
DATABASE_PATH = "backend/data/processed/documents.db"
RAW_DATA_PATH = "../../RawHTMLdata"

# Database settings
DB_BATCH_SIZE = 1000
DB_TIMEOUT = 30
DB_VACUUM_ON_STARTUP = False

# =============================================================================
# SEARCH ENGINE CONFIGURATION
# =============================================================================

# BM25 Algorithm Parameters
BM25_K1 = 1.5          # Term frequency saturation point
BM25_B = 0.75           # Field length normalization
BM25_MIN_TERM_LENGTH = 3 # Minimum term length for indexing

# Search Settings
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
SEARCH_TIMEOUT_MS = 5000

# Content Processing
CONTENT_PREVIEW_LENGTH = 300
TITLE_WEIGHT_MULTIPLIER = 2  # How many times title appears in index

# =============================================================================
# AI CONFIGURATION
# =============================================================================

# AI Model Preferences (in order of priority)
AI_MODEL_PREFERENCE = [
    "smart_template",  # Default: no downloads required
    "openai_gpt",      # Cloud-based
    "ollama",          # Local models
    "transformers"     # Hugging Face models
]

# OpenAI Configuration
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 150
OPENAI_TEMPERATURE = 0.3
OPENAI_TIMEOUT = 30

# Local Model Configuration
LOCAL_SUMMARIZATION_MODEL = "facebook/bart-large-cnn"
LOCAL_MAX_LENGTH = 100
LOCAL_MIN_LENGTH = 30

# Ollama Configuration
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama2"  # or "mistral", "codellama"
OLLAMA_TIMEOUT = 30

# Smart Template Configuration
SMART_SUMMARY_MAX_FACTS = 3
SMART_SUMMARY_FACT_LENGTH = 150

# =============================================================================
# TOPIC DETECTION CONFIGURATION
# =============================================================================

TOPIC_KEYWORDS = {
    'programming': [
        'python', 'javascript', 'programming', 'code', 'software', 
        'development', 'algorithm', 'function', 'variable', 'api'
    ],
    'machine_learning': [
        'machine', 'learning', 'neural', 'network', 'model', 
        'training', 'data', 'algorithm', 'prediction', 'classification'
    ],
    'web_development': [
        'html', 'css', 'web', 'frontend', 'backend', 'server', 
        'client', 'browser', 'framework', 'responsive'
    ],
    'data_science': [
        'data', 'analysis', 'statistics', 'visualization', 'pandas', 
        'numpy', 'dataset', 'research', 'analytics'
    ],
    'technology': [
        'technology', 'tech', 'innovation', 'digital', 'computer', 
        'system', 'platform', 'device', 'application'
    ],
    'business': [
        'business', 'company', 'management', 'strategy', 'market', 
        'revenue', 'customer', 'service', 'enterprise'
    ],
    'education': [
        'education', 'learning', 'course', 'tutorial', 'guide', 
        'teaching', 'student', 'university', 'academic'
    ],
    'health': [
        'health', 'medical', 'healthcare', 'medicine', 'treatment', 
        'patient', 'doctor', 'disease', 'therapy'
    ]
}

# =============================================================================
# DATA PIPELINE CONFIGURATION
# =============================================================================

# Processing Settings
PROCESSING_BATCH_SIZE = 100
PROCESSING_THREAD_COUNT = 4
PROCESSING_LOG_INTERVAL = 500

# Content Cleaning
MIN_CONTENT_LENGTH = 50
MAX_CONTENT_LENGTH = 50000
DUPLICATE_THRESHOLD = 0.9

# URL Filtering
BLOCKED_DOMAINS = [
    'spam-domain.com',
    'malicious-site.org'
]

ALLOWED_CONTENT_TYPES = [
    'text/html',
    'application/xhtml+xml'
]

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE_PATH = "logs/ai_search.log"

# Component-specific logging
COMPONENT_LOG_LEVELS = {
    "backend.search": "INFO",
    "backend.api": "INFO", 
    "data_pipeline.processor": "INFO",
    "frontend.components": "INFO"
}

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================

# Memory Settings
MAX_MEMORY_USAGE_MB = 1024
INDEX_CACHE_SIZE = 500

# Concurrency
MAX_CONCURRENT_SEARCHES = 100
API_RATE_LIMIT_PER_MINUTE = 1000

# Monitoring
ENABLE_PERFORMANCE_MONITORING = True
PERFORMANCE_LOG_INTERVAL = 60  # seconds

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# CORS Settings
CORS_ALLOW_ORIGINS = ["*"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# API Security
API_KEY_REQUIRED = False
API_KEY_HEADER = "X-API-Key"

# Content Security
SANITIZE_HTML_CONTENT = True
MAX_QUERY_LENGTH = 500

# =============================================================================
# DEVELOPMENT CONFIGURATION
# =============================================================================

# Development Mode
DEBUG_MODE = True
ENABLE_AUTO_RELOAD = True
ENABLE_DETAILED_ERRORS = True

# Testing
TEST_DATABASE_PATH = "backend/data/test/test_documents.db"
TEST_DATA_SIZE_LIMIT = 1000

# Build Settings
BUILD_OUTPUT_DIR = "dist"
STATIC_FILES_DIR = "frontend/build"

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Enable/Disable Features
ENABLE_AI_SUMMARIZATION = True
ENABLE_VECTOR_SEARCH = False
ENABLE_SEARCH_ANALYTICS = True
ENABLE_CACHING = False
ENABLE_SEARCH_SUGGESTIONS = True

# Experimental Features
ENABLE_SEMANTIC_SEARCH = False
ENABLE_MULTI_LANGUAGE_SUPPORT = False
ENABLE_REAL_TIME_INDEXING = False
