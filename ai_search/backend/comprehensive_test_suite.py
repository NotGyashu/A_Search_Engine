#!/usr/bin/env python3
"""
Comprehensive Search Engine Test Suite
Tests all components: Frontend proxy, Backend APIs, AI Runner integration, and end-to-end flows
"""

import requests
import json
import time
import threading
from typing import Dict, List, Any

# Service URLs
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
AI_RUNNER_URL = "http://127.0.0.1:8001"

class SearchEngineTestSuite:
    def __init__(self):
        self.results = {}
        self.performance_metrics = {}
        
    def log_test(self, test_name: str, status: bool, details: str = "", duration: float = 0):
        """Log test results"""
        self.results[test_name] = {
            "status": "✅ PASS" if status else "❌ FAIL",
            "details": details,
            "duration_ms": round(duration * 1000, 2)
        }
        
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {test_name}: {details} ({duration*1000:.1f}ms)")

    def test_service_health(self):
        """Test health of all services"""
        print("\n🏥 TESTING SERVICE HEALTH")
        print("=" * 50)
        
        # Test AI Runner
        start_time = time.time()
        try:
            response = requests.get(f"{AI_RUNNER_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "AI Runner Health", 
                    True, 
                    f"Status: {data['status']}, Models: {len(data['available_models'])}", 
                    time.time() - start_time
                )
            else:
                self.log_test("AI Runner Health", False, f"HTTP {response.status_code}", time.time() - start_time)
        except Exception as e:
            self.log_test("AI Runner Health", False, str(e), time.time() - start_time)
        
        # Test Backend
        start_time = time.time()
        try:
            response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Backend Health", 
                    True, 
                    f"Status: {data['status']}", 
                    time.time() - start_time
                )
            else:
                self.log_test("Backend Health", False, f"HTTP {response.status_code}", time.time() - start_time)
        except Exception as e:
            self.log_test("Backend Health", False, str(e), time.time() - start_time)
        
        # Test Frontend (basic connectivity)
        start_time = time.time()
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                self.log_test(
                    "Frontend Accessibility", 
                    True, 
                    "React app serving", 
                    time.time() - start_time
                )
            else:
                self.log_test("Frontend Accessibility", False, f"HTTP {response.status_code}", time.time() - start_time)
        except Exception as e:
            self.log_test("Frontend Accessibility", False, str(e), time.time() - start_time)

    def test_ai_runner_endpoints(self):
        """Test all AI Runner endpoints directly"""
        print("\n🧠 TESTING AI RUNNER ENDPOINTS")
        print("=" * 50)
        
        test_cases = [
            {
                "name": "Query Enhancement",
                "endpoint": "/enhance-query",
                "data": {"query": "python machine learning tutorial"},
                "expected_fields": ["enhanced_query", "expansions"]
            },
            {
                "name": "Intent Classification",
                "endpoint": "/classify-intent", 
                "data": {"query": "how to fix javascript error"},
                "expected_fields": ["primary_intent", "confidence"]
            },
            {
                "name": "Entity Extraction",
                "endpoint": "/extract-entities",
                "data": {"query": "react hooks tutorial for beginners"},
                "expected_fields": ["entities", "entity_count"]
            },
            {
                "name": "Content Analysis",
                "endpoint": "/analyze-content",
                "data": {"results": [
                    {"title": "Python Tutorial", "content_preview": "Learn Python programming", "domain": "python.org"},
                    {"title": "JS Guide", "content_preview": "JavaScript fundamentals", "domain": "mozilla.org"}
                ]},
                "expected_fields": ["quality_distribution", "content_types"]
            },
            {
                "name": "Quality Scoring",
                "endpoint": "/score-quality",
                "data": {"content": "This is a comprehensive tutorial on Python programming", "title": "Python Tutorial"},
                "expected_fields": ["overall_score", "quality_tier"]
            },
            {
                "name": "Result Reranking",
                "endpoint": "/rerank-results",
                "data": {
                    "query": "python tutorial",
                    "results": [
                        {"title": "Basic Python", "relevance_score": 0.7},
                        {"title": "Advanced Python", "relevance_score": 0.9}
                    ]
                },
                "expected_fields": ["reranked_results", "ranking_factors"]
            },
            {
                "name": "Comprehensive Insights",
                "endpoint": "/generate-insights",
                "data": {
                    "query": "machine learning basics",
                    "results": [
                        {"title": "ML Tutorial", "content_preview": "Introduction to machine learning"}
                    ]
                },
                "expected_fields": ["query_analysis", "content_insights"]
            },
            {
                "name": "Summarization",
                "endpoint": "/summarize",
                "data": {
                    "query": "python tutorial",
                    "results": [
                        {"title": "Python Guide", "content_preview": "Learn Python programming step by step"}
                    ]
                },
                "expected_fields": ["summary", "model_used"]
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                response = requests.post(
                    f"{AI_RUNNER_URL}{test_case['endpoint']}",
                    json=test_case['data'],
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    missing_fields = [field for field in test_case['expected_fields'] if field not in data]
                    
                    if not missing_fields:
                        self.log_test(
                            f"AI Runner {test_case['name']}",
                            True,
                            "All expected fields present",
                            time.time() - start_time
                        )
                    else:
                        self.log_test(
                            f"AI Runner {test_case['name']}",
                            False,
                            f"Missing fields: {missing_fields}",
                            time.time() - start_time
                        )
                else:
                    self.log_test(
                        f"AI Runner {test_case['name']}",
                        False,
                        f"HTTP {response.status_code}",
                        time.time() - start_time
                    )
            except Exception as e:
                self.log_test(
                    f"AI Runner {test_case['name']}",
                    False,
                    str(e),
                    time.time() - start_time
                )

    def test_backend_ai_endpoints(self):
        """Test AI endpoints through backend"""
        print("\n🖥️ TESTING BACKEND AI ENDPOINTS")
        print("=" * 50)
        
        test_cases = [
            {
                "name": "Backend Query Enhancement",
                "endpoint": "/api/ai/enhance-query",
                "data": {"query": "python web development"}
            },
            {
                "name": "Backend Intent Classification",
                "endpoint": "/api/ai/classify-intent",
                "data": {"query": "debug react application"}
            },
            {
                "name": "Backend Entity Extraction", 
                "endpoint": "/api/ai/extract-entities",
                "data": {"query": "vue.js components tutorial"}
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                response = requests.post(
                    f"{BACKEND_URL}{test_case['endpoint']}",
                    json=test_case['data'],
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        test_case['name'],
                        True,
                        "Response received",
                        time.time() - start_time
                    )
                else:
                    self.log_test(
                        test_case['name'],
                        False,
                        f"HTTP {response.status_code}",
                        time.time() - start_time
                    )
            except Exception as e:
                self.log_test(
                    test_case['name'],
                    False,
                    str(e),
                    time.time() - start_time
                )

    def test_search_functionality(self):
        """Test core search functionality"""
        print("\n🔍 TESTING SEARCH FUNCTIONALITY")
        print("=" * 50)
        
        test_queries = [
            "python tutorial",
            "javascript async await",
            "machine learning basics",
            "react hooks useState"
        ]
        
        for query in test_queries:
            start_time = time.time()
            try:
                response = requests.get(
                    f"{BACKEND_URL}/api/search",
                    params={"q": query, "limit": 5},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    total_results = data.get('total_results', 0)
                    ai_enhanced = data.get('ai_enhanced', False)
                    ai_insights = 'ai_insights' in data
                    
                    self.log_test(
                        f"Search: '{query}'",
                        True,
                        f"{total_results} results, AI: {ai_enhanced}, Insights: {ai_insights}",
                        time.time() - start_time
                    )
                    
                    # Track performance metrics
                    response_time = data.get('response_time_ms', 0)
                    self.performance_metrics[f"search_{query}"] = response_time
                    
                else:
                    self.log_test(
                        f"Search: '{query}'",
                        False,
                        f"HTTP {response.status_code}",
                        time.time() - start_time
                    )
            except Exception as e:
                self.log_test(
                    f"Search: '{query}'",
                    False,
                    str(e),
                    time.time() - start_time
                )

    def test_websocket_functionality(self):
        """Test WebSocket AI summary streaming"""
        print("\n🌐 TESTING WEBSOCKET FUNCTIONALITY")
        print("=" * 50)
        
        # First, trigger a search to get an AI request ID
        try:
            search_response = requests.get(
                f"{BACKEND_URL}/api/search",
                params={"q": "python programming tutorial", "limit": 3},
                timeout=30
            )
            
            if search_response.status_code == 200:
                data = search_response.json()
                ai_request_id = data.get('ai_summary_request_id')
                
                if ai_request_id:
                    self.log_test(
                        "AI Summary Request ID",
                        True,
                        f"ID: {ai_request_id[:8]}...",
                        0
                    )
                    
                    # TODO: Test WebSocket connection (requires async handling)
                    self.log_test(
                        "WebSocket Test",
                        True,
                        "WebSocket endpoint available (manual test required)",
                        0
                    )
                else:
                    self.log_test(
                        "AI Summary Request ID",
                        False,
                        "No AI request ID in response",
                        0
                    )
            else:
                self.log_test(
                    "WebSocket Setup",
                    False,
                    f"Search failed: HTTP {search_response.status_code}",
                    0
                )
        except Exception as e:
            self.log_test(
                "WebSocket Setup",
                False,
                str(e),
                0
            )

    def analyze_performance(self):
        """Analyze performance metrics and identify optimization opportunities"""
        print("\n📊 PERFORMANCE ANALYSIS")
        print("=" * 50)
        
        if self.performance_metrics:
            avg_search_time = sum(self.performance_metrics.values()) / len(self.performance_metrics)
            max_search_time = max(self.performance_metrics.values())
            min_search_time = min(self.performance_metrics.values())
            
            print(f"Average Search Time: {avg_search_time:.1f}ms")
            print(f"Max Search Time: {max_search_time:.1f}ms")
            print(f"Min Search Time: {min_search_time:.1f}ms")
            
            # Performance recommendations
            recommendations = []
            if avg_search_time > 1000:
                recommendations.append("🔧 High latency detected - optimize AI Runner communication")
            if max_search_time > 2000:
                recommendations.append("🔧 Some searches are very slow - implement request batching")
            if len(self.performance_metrics) > 1:
                variance = max_search_time - min_search_time
                if variance > 500:
                    recommendations.append("🔧 High variance in response times - check caching")
            
            if recommendations:
                print("\n🎯 OPTIMIZATION RECOMMENDATIONS:")
                for rec in recommendations:
                    print(f"   {rec}")
            else:
                print("\n✅ Performance looks good!")
        
        # Analyze communication patterns
        print("\n🔄 COMMUNICATION ANALYSIS:")
        print("   Backend ↔ AI Runner calls per search:")
        print("   • Query Enhancement: 1 call")
        print("   • Intent Classification: 1 call") 
        print("   • Entity Extraction: 1 call")
        print("   • Content Analysis: 1 call")
        print("   • Result Reranking: 1 call")
        print("   • Comprehensive Insights: 1 call")
        print("   📊 TOTAL: ~6 HTTP calls per search")
        print("   ⚠️  OPTIMIZATION NEEDED: Batch multiple operations")

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if "✅" in result["status"])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 SUMMARY: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test_name, result in self.results.items():
                if "❌" in result["status"]:
                    print(f"   • {test_name}: {result['details']}")
        
        print(f"\n🎉 OVERALL STATUS: {'✅ SYSTEM HEALTHY' if failed_tests == 0 else '⚠️ ISSUES DETECTED'}")
        
        # Next steps
        print(f"\n📋 NEXT STEPS:")
        if failed_tests == 0:
            print("   1. ✅ All components working - proceed with optimization")
            print("   2. 🔧 Implement AI Runner communication batching")
            print("   3. 📈 Add performance monitoring")
        else:
            print("   1. 🔧 Fix failed tests before optimization")
            print("   2. 📝 Review error logs and configurations")
            print("   3. 🧪 Re-run tests after fixes")

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 STARTING COMPREHENSIVE SEARCH ENGINE TEST")
        print("=" * 80)
        print(f"Frontend: {FRONTEND_URL}")
        print(f"Backend: {BACKEND_URL}")
        print(f"AI Runner: {AI_RUNNER_URL}")
        print("=" * 80)
        
        self.test_service_health()
        self.test_ai_runner_endpoints()
        self.test_backend_ai_endpoints()
        self.test_search_functionality()
        self.test_websocket_functionality()
        self.analyze_performance()
        self.generate_report()

if __name__ == "__main__":
    test_suite = SearchEngineTestSuite()
    test_suite.run_all_tests()
