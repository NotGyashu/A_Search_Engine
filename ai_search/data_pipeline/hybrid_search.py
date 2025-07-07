# Hybrid Cost-Effective Search Engine
# Uses free components for most operations, paid APIs only when needed

import os
from typing import List, Dict, Optional
import json
from pathlib import Path

class HybridSearchEngine:
    """Cost-optimized search engine using hybrid approach"""
    
    def __init__(self):
        self.free_search_enabled = True
        self.paid_llm_enabled = False  # Only enable for premium features
        
        # Free tier limits
        self.daily_llm_calls = 0
        self.max_daily_llm_calls = 10  # Limit expensive calls
        
        # Cost tracking
        self.daily_cost = 0.0
        self.monthly_budget = 50.0  # $50/month budget
    
    def should_use_paid_llm(self, query_complexity: str = "simple") -> bool:
        """Decide whether to use paid LLM based on budget and complexity"""
        
        if not self.paid_llm_enabled:
            return False
        
        if self.daily_cost > (self.monthly_budget / 30):  # Daily budget exceeded
            return False
        
        if self.daily_llm_calls >= self.max_daily_llm_calls:
            return False
        
        # Only use for complex queries
        complex_indicators = ["explain", "analyze", "compare", "why", "how"]
        return any(indicator in query_complexity.lower() for indicator in complex_indicators)
    
    def search_with_budget_control(self, query: str, user_tier: str = "free") -> Dict:
        """Perform search with cost controls"""
        
        # Always start with free semantic search
        free_results = self.free_semantic_search(query)
        
        response = {
            "query": query,
            "results": free_results,
            "answer_type": "free",
            "cost": 0.0
        }
        
        # Decide on answer generation method
        if user_tier == "premium" and self.should_use_paid_llm(query):
            # Use paid LLM for premium users only
            ai_answer = self.generate_ai_answer(query, free_results)
            response.update({
                "ai_answer": ai_answer,
                "answer_type": "ai_generated",
                "cost": 0.02  # Estimated cost
            })
            self.daily_llm_calls += 1
            self.daily_cost += 0.02
        else:
            # Use free answer generation
            response["answer"] = self.generate_free_answer(query, free_results)
        
        return response
    
    def free_semantic_search(self, query: str) -> List[Dict]:
        """Free semantic search using local models"""
        # Implementation using free sentence transformers + FAISS
        # This costs $0 to run
        return [
            {"text": "Sample result 1", "url": "example1.com", "score": 0.95},
            {"text": "Sample result 2", "url": "example2.com", "score": 0.87},
        ]
    
    def generate_free_answer(self, query: str, results: List[Dict]) -> str:
        """Generate answer without API costs"""
        # Option 1: Template-based responses
        if not results:
            return f"No results found for '{query}'. Try a different search term."
        
        # Option 2: Extractive summarization (free)
        context = " ".join([r["text"][:100] for r in results[:3]])
        
        # Simple keyword-based answer generation
        answer = f"Here's what I found about '{query}':\n\n"
        for i, result in enumerate(results[:3], 1):
            answer += f"{i}. {result['text'][:150]}...\n"
            answer += f"   Source: {result['url']}\n\n"
        
        return answer
    
    def generate_ai_answer(self, query: str, results: List[Dict]) -> str:
        """Generate AI answer using paid API (only for premium users)"""
        # This would call OpenAI/Anthropic API
        # Estimated cost: $0.01-0.05 per query
        
        context = "\n".join([r["text"] for r in results[:3]])
        
        # Mock API call (implement with actual API)
        return f"AI-generated comprehensive answer for '{query}' based on search results..."

# Free deployment options
DEPLOYMENT_OPTIONS = {
    "completely_free": {
        "hosting": "Vercel/Netlify (free tier)",
        "database": "SQLite + local files",
        "ai_models": "Sentence Transformers (local)",
        "vector_db": "FAISS (local)",
        "monthly_cost": "$0",
        "limitations": "Local processing only, no advanced AI answers"
    },
    
    "low_cost": {
        "hosting": "Railway/Render ($5/month)",
        "database": "PostgreSQL + pgvector ($0-10/month)",
        "ai_models": "OpenAI API ($10-20/month with limits)",
        "vector_db": "Local FAISS",
        "monthly_cost": "$15-35",
        "features": "Full AI answers, cloud hosting, scalable"
    },
    
    "production": {
        "hosting": "AWS/GCP ($20-50/month)",
        "database": "Managed PostgreSQL ($15-30/month)",
        "ai_models": "OpenAI + Anthropic APIs ($50-200/month)",
        "vector_db": "Pinecone ($20/month)",
        "monthly_cost": "$105-300",
        "features": "Full production scale, monitoring, CDN"
    }
}

# Resume-friendly cost optimization
def create_cost_optimization_demo():
    """Create a demo showing cost-conscious engineering"""
    
    print("🎯 AI Search Engine - Cost Optimization Demo")
    print("="*50)
    
    for tier, config in DEPLOYMENT_OPTIONS.items():
        print(f"\n📊 {tier.upper()} TIER:")
        print(f"   💰 Monthly cost: {config['monthly_cost']}")
        print(f"   🏗️  Hosting: {config['hosting']}")
        print(f"   🤖 AI Models: {config['ai_models']}")
        print(f"   📦 Vector DB: {config['vector_db']}")
        
        if 'limitations' in config:
            print(f"   ⚠️  Limitations: {config['limitations']}")
        if 'features' in config:
            print(f"   ✨ Features: {config['features']}")

if __name__ == "__main__":
    create_cost_optimization_demo()
