#!/usr/bin/env python3
"""
Test script for AI Runner microservice
"""

import requests
import json
import time

AI_RUNNER_URL = "http://127.0.0.1:8001"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{AI_RUNNER_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Available models: {data['available_models']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_summarization():
    """Test summarization endpoint"""
    print("\n📝 Testing summarization...")
    
    test_data = {
        "query": "Python programming",
        "results": [
            {
                "title": "Python Tutorial - Learn Python Programming",
                "content_preview": "Python is a high-level programming language that's easy to learn and widely used for web development, data science, and automation.",
                "domain": "tutorial.com",
                "url": "https://tutorial.com/python"
            },
            {
                "title": "Python Documentation",
                "content_preview": "Official Python documentation covering all language features, standard library, and best practices.",
                "domain": "python.org",
                "url": "https://python.org/docs"
            }
        ],
        "max_length": 200
    }
    
    try:
        response = requests.post(
            f"{AI_RUNNER_URL}/summarize",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Summarization successful!")
            print(f"   Model used: {data['model_used']}")
            print(f"   Generation time: {data['generation_time_ms']}ms")
            print(f"   Summary: {data['summary']}")
            return True
        else:
            print(f"❌ Summarization failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Summarization error: {e}")
        return False

def test_stats():
    """Test stats endpoint"""
    print("\n📊 Testing stats endpoint...")
    try:
        response = requests.get(f"{AI_RUNNER_URL}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stats retrieved successfully")
            print(f"   Available models: {data['available_models']}")
            print(f"   Primary model: {data['primary_model']}")
            print(f"   Service status: {data['service_status']}")
            return True
        else:
            print(f"❌ Stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 AI Runner Test Suite")
    print("=" * 40)
    
    # Check if AI Runner is running
    try:
        response = requests.get(f"{AI_RUNNER_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ AI Runner is not running!")
            print("   Start it with: cd ai_search/ai_runner && python app.py")
            return
    except:
        print("❌ AI Runner is not accessible!")
        print("   Start it with: cd ai_search/ai_runner && python app.py")
        return
    
    print("✅ AI Runner is running")
    
    # Run tests
    results = []
    results.append(test_health())
    results.append(test_stats())
    results.append(test_summarization())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 40)
    print(f"🎯 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! AI Runner is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()
