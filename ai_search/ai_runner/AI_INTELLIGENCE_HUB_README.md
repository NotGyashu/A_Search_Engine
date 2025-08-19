# 🧠 AI Intelligence Hub

## Overview
The AI Intelligence Hub is a sophisticated microservice that transforms the basic AI Runner into a comprehensive AI-powered search enhancement platform. It provides intelligent query processing, content analysis, and adaptive search capabilities.

## 🚀 Capabilities

### Phase 1: Query Intelligence
- **Query Enhancement** (`/enhance-query`): Expands queries with related terms and synonyms
- **Intent Classification** (`/classify-intent`): Identifies search intent (tutorial, troubleshooting, reference, general)
- **Entity Extraction** (`/extract-entities`): Identifies key entities and concepts in queries

### Phase 2: Content Analysis
- **Content Analysis** (`/analyze-content`): Comprehensive analysis of search results including quality scoring and duplicate detection
- **Quality Scoring** (`/score-quality`): Rates content quality based on multiple factors
- **Result Reranking** (`/rerank-results`): Reorders results based on relevance and quality

### Comprehensive Integration
- **Generate Insights** (`/generate-insights`): End-to-end AI analysis combining all capabilities
- **Summarization** (`/summarize`): Legacy-compatible summarization with enhanced context

## 🏗️ Architecture

### Modular Design
```
ai_search/ai_runner/
├── app.py                      # FastAPI application with all endpoints
├── ai_service.py              # Core orchestration service
├── services/
│   ├── query_intelligence.py # Phase 1 capabilities
│   └── content_analysis.py   # Phase 2 capabilities
└── test_comprehensive.py     # Full test suite
```

### Multi-Model Support
- **Google Gemini 2.5 Flash**: Primary model for complex analysis
- **OpenAI GPT**: Fallback for advanced reasoning
- **Transformers**: Local models for basic processing
- **Smart Template**: Pattern-based fallback for reliability

## 🎯 Performance Features

### Intelligent Caching
- In-memory caching for frequently requested analyses
- TTL-based cache expiration
- Smart cache key generation

### Optimized Processing
- Sub-5ms response times for cached queries
- Parallel processing for multiple operations
- Graceful fallback between models

## 📊 Monitoring & Health

### Health Checks
- `/health`: Comprehensive service health with model availability
- `/stats`: Detailed service statistics and performance metrics
- Real-time logging with structured output

### Production Ready
- Error handling and graceful degradation
- Model fallback chains
- Performance monitoring
- Comprehensive test coverage

## 🧪 Testing

Run the comprehensive test suite:
```bash
cd ai_search/ai_runner
python test_comprehensive.py
```

Tests cover:
- All Phase 1 & 2 endpoints
- Edge cases and error handling
- Performance benchmarks
- Real-world scenarios

## 🔄 Integration

The AI Intelligence Hub integrates seamlessly with:
- **Backend**: Enhanced search service with metadata-rich results
- **Frontend**: Intelligent result presentation and user insights
- **Data Pipeline**: Quality-scored and categorized content

## 📈 Future Extensibility

The modular architecture supports easy addition of:
- New AI models and providers
- Additional analysis capabilities
- Custom scoring algorithms
- Advanced caching strategies

---

**Status**: ✅ Production Ready | **Version**: 2.0 | **Last Updated**: January 2025
