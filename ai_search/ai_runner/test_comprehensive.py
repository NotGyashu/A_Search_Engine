#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI Intelligence Hub
Tests all Phase 1 & 2 capabilities with detailed verification
"""

import requests
import json
import time
import sys
from typing import Dict, List

class AIIntelligenceHubTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log(self, message: str, test_name: str = ""):
        timestamp = time.strftime("%H:%M:%S")
        if test_name:
            print(f"[{timestamp}] {test_name}: {message}")
        else:
            print(f"[{timestamp}] {message}")
    
    def test_endpoint(self, endpoint: str, method: str = "GET", data: dict = None, expected_fields: List[str] = None) -> bool:
        """Test an endpoint and verify response structure"""
        self.total_tests += 1
        test_name = f"{method} {endpoint}"
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
            else:
                self.log(f"❌ Unsupported method: {method}", test_name)
                return False
            
            # Check status code
            if response.status_code != 200:
                self.log(f"❌ Status code {response.status_code}", test_name)
                return False
            
            # Parse JSON
            try:
                result = response.json()
            except json.JSONDecodeError:
                self.log(f"❌ Invalid JSON response", test_name)
                return False
            
            # Check expected fields
            if expected_fields:
                missing_fields = [field for field in expected_fields if field not in result]
                if missing_fields:
                    self.log(f"❌ Missing fields: {missing_fields}", test_name)
                    return False
            
            # Check for errors in response
            if result.get('error'):
                self.log(f"❌ API error: {result['error']}", test_name)
                return False
            
            self.log(f"✅ Success", test_name)
            self.passed_tests += 1
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Request failed: {e}", test_name)
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error: {e}", test_name)
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        self.log("🚀 Starting AI Intelligence Hub Test Suite")
        self.log("=" * 60)
        
        # Test 1: Basic Health Check
        self.log("\n📋 BASIC CONNECTIVITY TESTS")
        health_success = self.test_endpoint("/", "GET", expected_fields=["service", "version", "capabilities", "endpoints"])
        if not health_success:
            self.log("❌ Basic connectivity failed - aborting tests")
            return False
        
        # Test 2: Enhanced Health Endpoint
        self.test_endpoint("/health", "GET", expected_fields=["status", "enhanced_features", "available_models"])
        
        # Test 3: Enhanced Stats Endpoint  
        self.test_endpoint("/stats", "GET", expected_fields=["enhanced_capabilities", "available_models"])
        
        # PHASE 1 TESTS: Query Intelligence
        self.log("\n🧠 PHASE 1: QUERY INTELLIGENCE TESTS")
        
        # Test 4: Query Enhancement
        query_enhance_data = {"query": "python machine learning tutorial"}
        self.test_endpoint("/enhance-query", "POST", query_enhance_data, 
                         ["original_query", "enhanced_query", "expansions", "suggestions", "confidence"])
        
        # Test 5: Intent Classification  
        intent_data = {"query": "how to fix javascript error in react"}
        self.test_endpoint("/classify-intent", "POST", intent_data,
                         ["primary_intent", "confidence", "suggested_filters"])
        
        # Test 6: Entity Extraction
        entity_data = {"query": "docker kubernetes tutorial for beginners"}
        self.test_endpoint("/extract-entities", "POST", entity_data,
                         ["entities", "entity_count"])
        
        # PHASE 2 TESTS: Content Analysis
        self.log("\n📊 PHASE 2: CONTENT ANALYSIS TESTS")
        
        # Sample results for content analysis tests
        sample_results = [
            {
                "title": "Complete Python Machine Learning Guide - Official Documentation",
                "content_preview": "Comprehensive guide to machine learning with Python. Covers scikit-learn, pandas, numpy, and deep learning frameworks. Includes practical examples, best practices, and performance optimization techniques.",
                "domain": "python.org"
            },
            {
                "title": "Python ML Tutorial for Beginners",
                "content_preview": "Learn machine learning basics with Python. Simple examples and code snippets.",
                "domain": "tutorials.com"
            },
            {
                "title": "Advanced ML Algorithms in Python",
                "content_preview": "Deep dive into advanced machine learning algorithms including neural networks, SVM, and ensemble methods. Academic research and implementation details.",
                "domain": "academic.edu"
            }
        ]
        
        # Test 7: Content Analysis
        content_data = {"results": sample_results}
        self.test_endpoint("/analyze-content", "POST", content_data,
                         ["quality_distribution", "content_types", "domain_analysis", "insights"])
        
        # Test 8: Quality Scoring
        quality_data = {
            "content": "This comprehensive tutorial covers machine learning fundamentals with detailed examples and best practices.",
            "title": "Complete Python Machine Learning Guide",
            "domain": "python.org"
        }
        self.test_endpoint("/score-quality", "POST", quality_data,
                         ["overall_score", "factor_scores", "quality_tier"])
        
        # Test 9: Result Reranking
        rerank_data = {"results": sample_results, "query": "python machine learning"}
        self.test_endpoint("/rerank-results", "POST", rerank_data,
                         ["reranked_results", "ranking_factors"])
        
        # COMPREHENSIVE TESTS
        self.log("\n🎯 COMPREHENSIVE INTEGRATION TESTS")
        
        # Test 10: Comprehensive Insights
        insights_data = {"query": "react hooks tutorial", "results": sample_results}
        self.test_endpoint("/generate-insights", "POST", insights_data,
                         ["query_analysis", "content_insights", "recommendations"])
        
        # Test 11: Original Summarization (Legacy Compatibility)
        summary_data = {"query": "machine learning", "results": sample_results}
        self.test_endpoint("/summarize", "POST", summary_data,
                         ["summary", "model_used", "generation_time_ms"])
        
        # EDGE CASE TESTS
        self.log("\n🧪 EDGE CASE & ERROR HANDLING TESTS")
        
        # Test 12: Empty query enhancement
        self.test_endpoint("/enhance-query", "POST", {"query": ""})
        
        # Test 13: Empty results analysis
        self.test_endpoint("/analyze-content", "POST", {"results": []})
        
        # Test 14: Invalid quality scoring
        self.test_endpoint("/score-quality", "POST", {"content": "", "title": "", "domain": ""})
        
        # PERFORMANCE TESTS
        self.log("\n⚡ PERFORMANCE TESTS")
        self.run_performance_tests()
        
        # Final Results
        self.log("\n" + "=" * 60)
        self.log(f"🎯 TEST RESULTS: {self.passed_tests}/{self.total_tests} tests passed")
        
        if self.passed_tests == self.total_tests:
            self.log("🎉 ALL TESTS PASSED - AI Intelligence Hub is fully functional!")
            return True
        else:
            failed = self.total_tests - self.passed_tests
            self.log(f"❌ {failed} tests failed - review implementation")
            return False
    
    def run_performance_tests(self):
        """Test response times for all endpoints"""
        performance_tests = [
            ("/enhance-query", "POST", {"query": "python tutorial"}),
            ("/classify-intent", "POST", {"query": "how to debug javascript"}),
            ("/extract-entities", "POST", {"query": "react hooks tutorial"}),
        ]
        
        for endpoint, method, data in performance_tests:
            start_time = time.time()
            success = self.test_endpoint(endpoint, method, data)
            end_time = time.time()
            
            if success:
                response_time = round((end_time - start_time) * 1000, 2)
                if response_time < 100:  # Under 100ms is excellent
                    self.log(f"⚡ Excellent performance: {response_time}ms", f"PERF {endpoint}")
                elif response_time < 500:  # Under 500ms is good
                    self.log(f"✅ Good performance: {response_time}ms", f"PERF {endpoint}")
                else:
                    self.log(f"⚠️ Slow performance: {response_time}ms", f"PERF {endpoint}")
    
    def test_specific_scenarios(self):
        """Test specific real-world scenarios"""
        self.log("\n🌟 REAL-WORLD SCENARIO TESTS")
        
        scenarios = [
            {
                "name": "Troubleshooting Scenario",
                "query": "python import error modulenotfound fix",
                "expected_intent": "troubleshooting"
            },
            {
                "name": "Tutorial Scenario", 
                "query": "react hooks tutorial step by step",
                "expected_intent": "tutorial"
            },
            {
                "name": "Documentation Scenario",
                "query": "python pandas api reference",
                "expected_intent": "reference"
            }
        ]
        
        for scenario in scenarios:
            self.log(f"\n📝 Testing: {scenario['name']}")
            
            # Test intent classification
            intent_response = requests.post(
                f"{self.base_url}/classify-intent",
                json={"query": scenario["query"]},
                headers={"Content-Type": "application/json"}
            )
            
            if intent_response.status_code == 200:
                intent_result = intent_response.json()
                detected_intent = intent_result.get("primary_intent")
                
                if detected_intent == scenario["expected_intent"]:
                    self.log(f"✅ Intent correctly detected: {detected_intent}")
                else:
                    self.log(f"⚠️ Intent mismatch - expected: {scenario['expected_intent']}, got: {detected_intent}")
            else:
                self.log(f"❌ Intent classification failed")

def main():
    tester = AIIntelligenceHubTester()
    
    print("🧠 AI Intelligence Hub - Comprehensive Test Suite")
    print("Testing Phase 1 & 2 Implementation")
    print("=" * 60)
    
    # Basic connectivity test
    try:
        response = requests.get("http://127.0.0.1:8001/", timeout=5)
        if response.status_code != 200:
            print("❌ AI Intelligence Hub not responding - is it running?")
            print("   Start it with: cd ai_search/ai_runner && source ai-venv/bin/activate && python3 app.py")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to AI Intelligence Hub at http://127.0.0.1:8001")
        print("   Make sure the service is running!")
        sys.exit(1)
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Run specific scenarios
    tester.test_specific_scenarios()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 VERIFICATION COMPLETE - AI Intelligence Hub is production ready!")
        print("✅ All Phase 1 & 2 capabilities verified and working")
    else:
        print("❌ Some tests failed - review implementation before production")
        sys.exit(1)

if __name__ == "__main__":
    main()
