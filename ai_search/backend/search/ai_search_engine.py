#!/usr/bin/env python3
"""
Complete AI Search Engine Implementation
Adds semantic search capabilities to your existing keyword search
"""

import sqlite3
import time
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    print("✅ AI libraries loaded successfully")
    
    def build_ai_search_index():
        """Build the complete AI search index"""
        print("🏗️  Building AI Search Index...")
        print("=" * 50)
        
        # Load documents from database
        conn = sqlite3.connect('data/processed/documents.db')
        cursor = conn.cursor()
        cursor.execute('SELECT url, title, content, domain, word_count FROM documents ORDER BY word_count DESC')
        documents = cursor.fetchall()
        conn.close()
        
        print(f"📊 Loaded {len(documents)} documents")
        
        # Initialize embedding model (free, 22MB)
        print("🧠 Loading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create embeddings for documents
        print("🚀 Creating document embeddings...")
        texts = []
        for url, title, content, domain, word_count in documents:
            # Use title + first 500 chars for embedding
            text = f"{title} {content[:500]}"
            texts.append(text)
        
        # Create embeddings in batches
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = model.encode(batch, show_progress_bar=True)
            all_embeddings.extend(embeddings)
            print(f"   Processed {min(i + batch_size, len(texts))}/{len(texts)} documents")
        
        # Convert to numpy array
        embeddings_array = np.array(all_embeddings)
        
        # Create FAISS index
        print("🔧 Creating FAISS index...")
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings_array)
        index.add(embeddings_array.astype('float32'))
        
        # Save everything
        index_dir = Path('data/processed/ai_index')
        index_dir.mkdir(exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(index, str(index_dir / 'search_index.faiss'))
        
        # Save document metadata
        import pickle
        with open(index_dir / 'documents.pkl', 'wb') as f:
            pickle.dump(documents, f)
        
        print("\n🎉 AI SEARCH INDEX COMPLETE!")
        print("=" * 50)
        print(f"📊 Indexed {len(documents)} documents")
        print(f"🧠 Vector dimensions: {dimension}")
        print(f"💾 Index size: ~{embeddings_array.nbytes / 1024 / 1024:.1f} MB")
        print(f"🔍 Ready for semantic search!")
        print(f"💰 Total cost: $0.00")
        
        return True
        
    def ai_search(query, top_k=5):
        """Perform AI-powered semantic search"""
        print(f"\n🔍 AI Search: '{query}'")
        start_time = time.time()
        
        # Load model and index
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        index_dir = Path('data/processed/ai_index')
        index = faiss.read_index(str(index_dir / 'search_index.faiss'))
        
        import pickle
        with open(index_dir / 'documents.pkl', 'rb') as f:
            documents = pickle.load(f)
        
        # Encode query
        query_embedding = model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = index.search(query_embedding.astype('float32'), top_k)
        
        search_time = time.time() - start_time
        
        print(f"⚡ Found {len(indices[0])} results in {search_time:.3f}s")
        print(f"💰 Cost: $0.00 (local AI)")
        
        # Display results
        for i, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
            url, title, content, domain, word_count = documents[idx]
            print(f"\n{i}. {title}")
            print(f"   🌐 {url}")
            print(f"   📊 {domain} | {word_count:,} words | Score: {score:.3f}")
            print(f"   📝 {content[:150]}...")
        
        return True

except ImportError as e:
    print(f"❌ AI libraries not available: {e}")
    print("Your basic search engine works perfectly!")
    print("To add AI features, ensure you're in the venv with all packages installed.")
    
    def build_ai_search_index():
        print("❌ Cannot build AI index without sentence-transformers and faiss")
        return False
    
    def ai_search(query, top_k=5):
        print("❌ AI search not available. Using basic keyword search:")
        # Fall back to keyword search
        conn = sqlite3.connect('data/processed/documents.db')
        cursor = conn.cursor()
        
        search_query = f"%{query.lower()}%"
        cursor.execute('''
            SELECT url, title, content, domain, word_count 
            FROM documents 
            WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY word_count DESC
            LIMIT ?
        ''', (search_query, search_query, top_k))
        
        results = cursor.fetchall()
        conn.close()
        
        for i, (url, title, content, domain, word_count) in enumerate(results, 1):
            print(f"\n{i}. {title}")
            print(f"   🌐 {url}")
            print(f"   📊 {domain} | {word_count:,} words")
            print(f"   📝 {content[:150]}...")

def main():
    print("🤖 AI Search Engine Builder")
    print("=" * 40)
    
    # Check if AI index exists
    ai_index_path = Path('data/processed/ai_index/search_index.faiss')
    
    if not ai_index_path.exists():
        print("🏗️  Building AI search index...")
        if build_ai_search_index():
            print("\n✅ AI index built successfully!")
        else:
            print("\n❌ Could not build AI index")
            return
    else:
        print("📁 AI index already exists!")
    
    # Interactive search
    print("\n🔍 AI Search Engine Ready!")
    print("Type your questions, or 'quit' to exit")
    
    while True:
        query = input("\n➤ Search: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if query:
            ai_search(query)

if __name__ == "__main__":
    main()
