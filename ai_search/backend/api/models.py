"""
API Models - Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: Optional[int] = Field(10, ge=1, le=50, description="Maximum number of results")
    include_ai_summary: Optional[bool] = Field(True, description="Include AI-generated summary")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class SearchResult(BaseModel):
    """Individual search result model"""
    id: int
    url: str
    title: str
    content_preview: str
    domain: str
    word_count: int
    relevance_score: float = Field(..., ge=0, description="BM25 relevance score")


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    total_found: int
    search_time_ms: float
    search_method: str
    ai_summary: Optional[str] = None
    ai_model_used: Optional[str] = None
    ai_generation_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None


class DatabaseStats(BaseModel):
    """Database statistics model"""
    total_documents: int
    database_size_mb: float
    average_document_length: float
    top_domains: List[Dict[str, Any]]
    database_path: str


class SearchStats(BaseModel):
    """Search engine statistics model"""
    total_documents: int
    total_terms: int
    average_document_length: float
    bm25_parameters: Dict[str, Any]
    index_status: str


class AIStats(BaseModel):
    """AI service statistics model"""
    available_models: List[str]
    model_preference: List[str]
    default_model: str


class StatsResponse(BaseModel):
    """Complete statistics response"""
    database: DatabaseStats
    search: SearchStats
    ai: AIStats
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheck(BaseModel):
    """Health check model"""
    status: str = Field(..., pattern="^(healthy|unhealthy)$")
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict)


class ConfigResponse(BaseModel):
    """Configuration response model"""
    search_config: Dict[str, Any]
    ai_config: Dict[str, Any]
    server_config: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = Field(default="error")
    message: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None


# === AI INTELLIGENCE HUB MODELS ===

class AIQueryEnhanceRequest(BaseModel):
    """AI query enhancement request"""
    query: str = Field(..., min_length=1, description="Query to enhance")

class AIIntentClassifyRequest(BaseModel):
    """AI intent classification request"""
    query: str = Field(..., min_length=1, description="Query to classify")

class AIEntityExtractionRequest(BaseModel):
    """AI entity extraction request"""
    query: str = Field(..., min_length=1, description="Query to extract entities from")

class AIContentAnalysisRequest(BaseModel):
    """AI content analysis request"""
    results: List[Dict] = Field(..., description="Search results to analyze")

class AIQualityScoringRequest(BaseModel):
    """AI quality scoring request"""
    content: str = Field(..., description="Content to score")
    title: Optional[str] = Field("", description="Content title")
    domain: Optional[str] = Field("", description="Content domain")

class AIRerankingRequest(BaseModel):
    """AI result reranking request"""
    results: List[Dict] = Field(..., description="Results to rerank")
    query: str = Field(..., min_length=1, description="Original query")

class AIInsightsRequest(BaseModel):
    """AI comprehensive insights request"""
    query: str = Field(..., min_length=1, description="Search query")
    results: List[Dict] = Field(..., description="Search results")
