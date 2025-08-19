"""
AI Runner Microservice - Enhanced AI Intelligence Hub
Handles AI-powered operations including summarization, query intelligence, and content analysis
Supports multiple AI models and provides comprehensive search enhancement capabilities
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import time
import logging
import asyncio
from datetime import datetime
import uvicorn
from ai_service import AIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai_runner")

# Enhanced Pydantic models for new endpoints
class SummarizeRequest(BaseModel):
    query: str
    results: List[Dict]
    max_length: Optional[int] = 300

class SummarizeResponse(BaseModel):
    summary: str
    model_used: str
    generation_time_ms: float
    error: Optional[str] = None

class QueryEnhanceRequest(BaseModel):
    query: str

class QueryEnhanceResponse(BaseModel):
    original_query: str
    enhanced_query: str
    expansions: List[str]
    suggestions: List[str]
    corrections: List[Dict]
    entities: Dict
    confidence: float
    processing_time_ms: float
    error: Optional[str] = None

class IntentClassifyRequest(BaseModel):
    query: str

class IntentClassifyResponse(BaseModel):
    query: str
    primary_intent: str
    confidence: float
    all_intents: Dict
    suggested_filters: List[str]
    processing_time_ms: float
    error: Optional[str] = None

class EntityExtractionRequest(BaseModel):
    query: str

class EntityExtractionResponse(BaseModel):
    query: str
    entities: Dict
    entity_count: int
    processing_time_ms: float
    error: Optional[str] = None

class ContentAnalysisRequest(BaseModel):
    results: List[Dict]

class ContentAnalysisResponse(BaseModel):
    total_results: int
    quality_distribution: Dict
    content_types: Dict
    domain_analysis: Dict
    insights: List[str]
    processing_time_ms: float
    error: Optional[str] = None

class QualityScoringRequest(BaseModel):
    content: str
    title: Optional[str] = ""
    domain: Optional[str] = ""

class QualityScoringResponse(BaseModel):
    overall_score: float
    factor_scores: Dict
    quality_tier: str
    domain_boost: float
    processing_time_ms: float
    error: Optional[str] = None

class ResultRerankingRequest(BaseModel):
    results: List[Dict]
    query: str

class ResultRerankingResponse(BaseModel):
    reranked_results: List[Dict]
    ranking_factors: Dict
    processing_time_ms: float
    error: Optional[str] = None

class ComprehensiveInsightsRequest(BaseModel):
    query: str
    results: List[Dict]

class ComprehensiveInsightsResponse(BaseModel):
    query_analysis: Dict
    content_insights: List[str]
    quality_overview: Dict
    content_types: Dict
    authority_signals: Dict
    recommendations: List[str]
    processing_time_ms: float
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    available_models: List[str]
    uptime_seconds: float
    enhanced_features: Dict

class AIStatsResponse(BaseModel):
    available_models: List[str]
    primary_model: str
    service_status: str
    enhanced_capabilities: Dict

# Batch Operations Models
class BatchOperation(BaseModel):
    type: str  # enhance_query, classify_intent, extract_entities, etc.
    data: Dict

class BatchOperationsRequest(BaseModel):
    operations: List[BatchOperation]

class BatchOperationsResponse(BaseModel):
    results: Dict
    total_processing_time_ms: float
    operations_count: int
    individual_times: Dict
    error: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="AI Intelligence Hub",
    description="Enhanced AI-powered service with query intelligence, content analysis, and summarization",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AI service instance
ai_service = None
start_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Initialize AI service on startup"""
    global ai_service
    logger.info("� Starting AI Intelligence Hub...")
    ai_service = AIService()
    logger.info("✅ AI Intelligence Hub ready with enhanced capabilities")

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    """Generate AI summary of search results"""
    try:
        logger.info(f"📝 Summarization request: '{request.query}' with {len(request.results)} results")
        
        # Generate summary using AI service
        result = ai_service.generate_summary(
            query=request.query,
            results=request.results,
            max_length=request.max_length
        )
        
        response = SummarizeResponse(
            summary=result['summary'],
            model_used=result['model_used'],
            generation_time_ms=result['generation_time_ms'],
            error=result['error']
        )
        
        logger.info(f"✅ Summary generated using {result['model_used']} in {result['generation_time_ms']}ms")
        return response
        
    except Exception as e:
        logger.error(f"❌ Summarization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI summarization failed: {str(e)}"
        )

# === PHASE 1: QUERY INTELLIGENCE ENDPOINTS ===

@app.post("/enhance-query", response_model=QueryEnhanceResponse)
async def enhance_query(request: QueryEnhanceRequest):
    """Enhance query with expansions and suggestions"""
    try:
        logger.info(f"🔍 Query enhancement request: '{request.query}'")
        
        result = ai_service.enhance_query(request.query)
        
        response = QueryEnhanceResponse(
            original_query=result['original_query'],
            enhanced_query=result['enhanced_query'],
            expansions=result['expansions'],
            suggestions=result['suggestions'],
            corrections=result['corrections'],
            entities=result['entities'],
            confidence=result['confidence'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Query enhanced with {len(result['expansions'])} expansions")
        return response
        
    except Exception as e:
        logger.error(f"❌ Query enhancement failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query enhancement failed: {str(e)}"
        )

@app.post("/classify-intent", response_model=IntentClassifyResponse)
async def classify_intent(request: IntentClassifyRequest):
    """Classify the intent of a search query"""
    try:
        logger.info(f"🎯 Intent classification request: '{request.query}'")
        
        result = ai_service.classify_intent(request.query)
        
        response = IntentClassifyResponse(
            query=result['query'],
            primary_intent=result['primary_intent'],
            confidence=result['confidence'],
            all_intents=result['all_intents'],
            suggested_filters=result['suggested_filters'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Intent classified: {result['primary_intent']} ({result['confidence']:.2f})")
        return response
        
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Intent classification failed: {str(e)}"
        )

@app.post("/extract-entities", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """Extract entities from query (technologies, topics, levels, etc.)"""
    try:
        logger.info(f"🏷️ Entity extraction request: '{request.query}'")
        
        result = ai_service.extract_entities(request.query)
        
        response = EntityExtractionResponse(
            query=result['query'],
            entities=result['entities'],
            entity_count=result['entity_count'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Extracted {result['entity_count']} entities")
        return response
        
    except Exception as e:
        logger.error(f"❌ Entity extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Entity extraction failed: {str(e)}"
        )

# === PHASE 2: CONTENT ANALYSIS ENDPOINTS ===

@app.post("/analyze-content", response_model=ContentAnalysisResponse)
async def analyze_content(request: ContentAnalysisRequest):
    """Analyze content of search results for quality, type, and insights"""
    try:
        logger.info(f"📊 Content analysis request for {len(request.results)} results")
        
        result = ai_service.analyze_content(request.results)
        
        response = ContentAnalysisResponse(
            total_results=result['total_results'],
            quality_distribution=result['quality_distribution'],
            content_types=result['content_types'],
            domain_analysis=result['domain_analysis'],
            insights=result['insights'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Content analysis completed for {result['total_results']} results")
        return response
        
    except Exception as e:
        logger.error(f"❌ Content analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Content analysis failed: {str(e)}"
        )

@app.post("/score-quality", response_model=QualityScoringResponse)
async def score_quality(request: QualityScoringRequest):
    """Score the quality of individual content"""
    try:
        logger.info(f"⭐ Quality scoring request for: '{request.title[:50]}'")
        
        result = ai_service.score_quality(request.content, request.title, request.domain)
        
        response = QualityScoringResponse(
            overall_score=result['overall_score'],
            factor_scores=result['factor_scores'],
            quality_tier=result['quality_tier'],
            domain_boost=result['domain_boost'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Quality scored: {result['overall_score']:.3f} ({result['quality_tier']})")
        return response
        
    except Exception as e:
        logger.error(f"❌ Quality scoring failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quality scoring failed: {str(e)}"
        )

@app.post("/rerank-results", response_model=ResultRerankingResponse)
async def rerank_results(request: ResultRerankingRequest):
    """Rerank results based on content analysis and query relevance"""
    try:
        logger.info(f"📈 Result reranking request for {len(request.results)} results")
        
        result = ai_service.rerank_results(request.results, request.query)
        
        response = ResultRerankingResponse(
            reranked_results=result['reranked_results'],
            ranking_factors=result['ranking_factors'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Results reranked: {result['ranking_factors'].get('results_reordered', 0)} changes")
        return response
        
    except Exception as e:
        logger.error(f"❌ Result reranking failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Result reranking failed: {str(e)}"
        )

# === COMPREHENSIVE INSIGHTS ENDPOINT ===

@app.post("/generate-insights", response_model=ComprehensiveInsightsResponse)
async def generate_insights(request: ComprehensiveInsightsRequest):
    """Generate comprehensive insights combining query and content analysis"""
    try:
        logger.info(f"🧠 Comprehensive insights request: '{request.query}' with {len(request.results)} results")
        
        result = ai_service.generate_insights(request.query, request.results)
        
        response = ComprehensiveInsightsResponse(
            query_analysis=result['query_analysis'],
            content_insights=result['content_insights'],
            quality_overview=result['quality_overview'],
            content_types=result['content_types'],
            authority_signals=result['authority_signals'],
            recommendations=result['recommendations'],
            processing_time_ms=result['processing_time_ms'],
            error=result.get('error')
        )
        
        logger.info(f"✅ Comprehensive insights generated in {result['processing_time_ms']}ms")
        return response
        
    except Exception as e:
        logger.error(f"❌ Comprehensive insights failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Comprehensive insights failed: {str(e)}"
        )

# === BATCH OPERATIONS ENDPOINT (OPTIMIZATION) ===

@app.post("/batch-operations", response_model=BatchOperationsResponse)
async def batch_operations(request: BatchOperationsRequest):
    """Execute multiple AI operations in a single batch request for optimization"""
    try:
        logger.info(f"🚀 Batch operations request: {len(request.operations)} operations")
        start_time = time.time()
        
        results = {}
        individual_times = {}
        
        # Group operations by type for potential optimization
        query_ops = []
        content_ops = []
        
        for op in request.operations:
            if op.type in ['enhance_query', 'classify_intent', 'extract_entities']:
                query_ops.append(op)
            else:
                content_ops.append(op)
        
        # Execute query operations (can be parallel since they use same query)
        if query_ops:
            logger.info(f"🔍 Executing {len(query_ops)} query operations")
            for op in query_ops:
                op_start = time.time()
                
                if op.type == 'enhance_query':
                    result = ai_service.enhance_query(op.data.get('query', ''))
                elif op.type == 'classify_intent':
                    result = ai_service.classify_intent(op.data.get('query', ''))
                elif op.type == 'extract_entities':
                    result = ai_service.extract_entities(op.data.get('query', ''))
                
                results[op.type] = result
                individual_times[op.type] = round((time.time() - op_start) * 1000, 2)
        
        # Execute content operations
        if content_ops:
            logger.info(f"📊 Executing {len(content_ops)} content operations")
            for op in content_ops:
                op_start = time.time()
                
                if op.type == 'analyze_content':
                    result = ai_service.analyze_content(op.data.get('results', []))
                elif op.type == 'score_quality':
                    result = ai_service.score_quality(
                        op.data.get('content', ''),
                        op.data.get('title', ''),
                        op.data.get('domain', '')
                    )
                elif op.type == 'rerank_results':
                    result = ai_service.rerank_results(
                        op.data.get('results', []),
                        op.data.get('query', '')
                    )
                elif op.type == 'generate_insights':
                    result = ai_service.generate_insights(
                        op.data.get('query', ''),
                        op.data.get('results', [])
                    )
                elif op.type == 'summarize':
                    result = ai_service.generate_summary(
                        op.data.get('query', ''),
                        op.data.get('results', []),
                        op.data.get('max_length', 300)
                    )
                
                results[op.type] = result
                individual_times[op.type] = round((time.time() - op_start) * 1000, 2)
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        response = BatchOperationsResponse(
            results=results,
            total_processing_time_ms=total_time,
            operations_count=len(request.operations),
            individual_times=individual_times
        )
        
        logger.info(f"✅ Batch operations completed: {len(request.operations)} ops in {total_time}ms")
        return response
        
    except Exception as e:
        logger.error(f"❌ Batch operations failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch operations failed: {str(e)}"
        )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check endpoint"""
    try:
        # Check AI service health
        ai_health = ai_service.health_check() if ai_service else {"status": "not_initialized"}
        
        return HealthResponse(
            status="healthy" if ai_health.get("status") == "healthy" else "degraded",
            timestamp=datetime.now().isoformat(),
            version="2.0.0",
            available_models=ai_health.get("available_models", []),
            uptime_seconds=round(time.time() - start_time, 2),
            enhanced_features=ai_health.get("enhanced_features", {})
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/stats", response_model=AIStatsResponse)
async def get_ai_stats():
    """Get enhanced AI service statistics"""
    try:
        if not ai_service:
            raise HTTPException(status_code=503, detail="AI service not initialized")
        
        health = ai_service.health_check()
        
        return AIStatsResponse(
            available_models=health.get("available_models", []),
            primary_model=health.get("primary_model", "none"),
            service_status=health.get("status", "unknown"),
            enhanced_capabilities={
                "query_enhancement": health.get("enhanced_features", {}).get("query_enhancement", False),
                "intent_classification": health.get("enhanced_features", {}).get("intent_classification", False),
                "entity_extraction": health.get("enhanced_features", {}).get("entity_extraction", False),
                "content_analysis": health.get("enhanced_features", {}).get("content_analysis", False),
                "quality_scoring": health.get("enhanced_features", {}).get("quality_scoring", False),
                "result_reranking": health.get("enhanced_features", {}).get("result_reranking", False),
                "summarization": health.get("test_summary_working", False)
            }
        )
    except Exception as e:
        logger.error(f"Stats request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats unavailable: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with enhanced service information"""
    return {
        "service": "AI Intelligence Hub",
        "version": "2.0.0",
        "status": "running",
        "capabilities": {
            "summarization": "Generate AI summaries of search results",
            "query_enhancement": "Enhance queries with expansions and suggestions", 
            "intent_classification": "Classify search intent and suggest filters",
            "entity_extraction": "Extract technologies, topics, and entities",
            "content_analysis": "Analyze content quality and characteristics",
            "quality_scoring": "Score individual content quality",
            "result_reranking": "Rerank results based on quality and relevance",
            "comprehensive_insights": "Generate combined query and content insights",
            "batch_operations": "Execute multiple AI operations in a single optimized request"
        },
        "endpoints": {
            "summarization": "/summarize",
            "query_enhancement": "/enhance-query",
            "intent_classification": "/classify-intent", 
            "entity_extraction": "/extract-entities",
            "content_analysis": "/analyze-content",
            "quality_scoring": "/score-quality",
            "result_reranking": "/rerank-results",
            "comprehensive_insights": "/generate-insights",
            "batch_operations": "/batch-operations",
            "health": "/health",
            "stats": "/stats",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    logger.info("🚀 Starting AI Intelligence Hub server...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,  # Different port from main backend
        log_level="info"
    )
