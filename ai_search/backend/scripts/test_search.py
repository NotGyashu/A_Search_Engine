#!/usr/bin/env python3
"""Quick test of our search engine"""

import sys
from pathlib import Path

# Add the data_pipeline directory to the path
project_root = Path(__file__).parent.parent.parent.parent
data_pipeline_path = project_root / "ai_search" / "data_pipeline"
sys.path.append(str(data_pipeline_path))

from free_search import FreeSearchEngine

# Initialize search engine
engine = FreeSearchEngine()

# Load documents
doc_count = engine.load_documents()
print(f"Loaded {doc_count} documents")

if doc_count > 0:
    # Test search
    query = "python programming"
    print(f"\n🔍 Searching for: '{query}'")
    
    results = engine.search(query, top_k=5)
    
    print(f"Found {results['total_found']} results in {results['search_time']}")
    print(f"Method: {results['search_method']}")
    print(f"Cost: {results['cost']}")
    
    print("\n📄 TOP RESULTS:")
    for i, result in enumerate(results['results'], 1):
        print(f"\n{i}. {result.title}")
        print(f"   URL: {result.url}")
        print(f"   Domain: {result.domain}")
        print(f"   Words: {result.word_count}")
        print(f"   Score: {result.score}")
        print(f"   Preview: {result.content_preview[:100]}...")
else:
    print("No documents found. Check if document processing completed.")
