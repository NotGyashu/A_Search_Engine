#!/usr/bin/env python3
"""
Simple quality improvement verification script.
Checks one of the existing quality output files to show improvements.
"""

import json
from pathlib import Path

def analyze_quality_file(quality_file_path):
    """Analyze a quality output file and report on improvements."""
    
    print("🔍 QUALITY ANALYSIS REPORT")
    print("=" * 50)
    
    try:
        with open(quality_file_path, 'r') as f:
            data = json.load(f)
        
        documents = data.get('documents', [])
        chunks = data.get('chunks', [])
        quality_summary = data.get('quality_summary', {})
        
        print(f"📊 Processing Overview:")
        print(f"   Total Documents: {len(documents)}")
        print(f"   Total Chunks: {len(chunks)}")
        
        if not documents:
            print("❌ No documents found in quality file!")
            return
        
        # Analyze keywords quality
        print(f"\n🔑 Keyword Quality Analysis:")
        poor_keywords = ['get', 'make', 'use', 'how', 'what', 'the', 'and', 'for', 'with', 'you', 'here', 'click']
        
        total_poor_keywords = 0
        total_keywords = 0
        
        for doc in documents:
            doc_keywords = doc.get('keywords', [])
            total_keywords += len(doc_keywords)
            doc_poor = [kw for kw in doc_keywords if kw in poor_keywords]
            total_poor_keywords += len(doc_poor)
            
            if doc_poor:
                print(f"   ⚠️ Document {doc.get('url', 'unknown')[:50]}...")
                print(f"      Poor keywords: {', '.join(doc_poor)}")
        
        poor_keyword_percentage = (total_poor_keywords / max(total_keywords, 1)) * 100
        print(f"   📈 Poor Keywords: {total_poor_keywords}/{total_keywords} ({poor_keyword_percentage:.1f}%)")
        
        if poor_keyword_percentage < 20:
            print("   ✅ Keyword quality is GOOD!")
        elif poor_keyword_percentage < 40:
            print("   ⚠️ Keyword quality is MODERATE")
        else:
            print("   ❌ Keyword quality is POOR")
        
        # Analyze chunk sizes
        print(f"\n📝 Chunk Size Analysis:")
        if chunks:
            word_counts = [chunk.get('word_count', 0) for chunk in chunks]
            avg_words = sum(word_counts) / len(word_counts)
            min_words = min(word_counts)
            max_words = max(word_counts)
            
            small_chunks = len([wc for wc in word_counts if wc < 50])
            medium_chunks = len([wc for wc in word_counts if 50 <= wc < 150])
            large_chunks = len([wc for wc in word_counts if wc >= 150])
            
            print(f"   📊 Word Count Distribution:")
            print(f"      Small (<50 words): {small_chunks} chunks")
            print(f"      Medium (50-149 words): {medium_chunks} chunks")
            print(f"      Large (150+ words): {large_chunks} chunks")
            print(f"   📈 Stats: Min={min_words}, Avg={avg_words:.1f}, Max={max_words}")
            
            if avg_words >= 100 and small_chunks / len(chunks) < 0.3:
                print("   ✅ Chunk sizes are GOOD!")
            elif avg_words >= 70:
                print("   ⚠️ Chunk sizes are MODERATE")
            else:
                print("   ❌ Chunk sizes are POOR")
        
        # Analyze quality scores
        print(f"\n⭐ Quality Score Analysis:")
        if chunks:
            quality_scores = [chunk.get('quality_score', 0) for chunk in chunks]
            avg_quality = sum(quality_scores) / len(quality_scores)
            min_quality = min(quality_scores)
            max_quality = max(quality_scores)
            
            high_quality = len([qs for qs in quality_scores if qs >= 1.0])
            medium_quality = len([qs for qs in quality_scores if 0.5 <= qs < 1.0])
            low_quality = len([qs for qs in quality_scores if qs < 0.5])
            
            print(f"   📊 Quality Distribution:")
            print(f"      High Quality (≥1.0): {high_quality} chunks")
            print(f"      Medium Quality (0.5-0.99): {medium_quality} chunks")
            print(f"      Low Quality (<0.5): {low_quality} chunks")
            print(f"   📈 Stats: Min={min_quality:.2f}, Avg={avg_quality:.2f}, Max={max_quality:.2f}")
            
            if avg_quality >= 1.0 and low_quality / len(chunks) < 0.2:
                print("   ✅ Quality scores are EXCELLENT!")
            elif avg_quality >= 0.7:
                print("   ⚠️ Quality scores are MODERATE")
            else:
                print("   ❌ Quality scores are POOR")
        
        # Sample content analysis
        print(f"\n📄 Sample Content Analysis:")
        if chunks:
            print(f"   First chunk sample:")
            sample_chunk = chunks[0]
            print(f"      URL: {sample_chunk.get('document_id', 'unknown')}")
            print(f"      Words: {sample_chunk.get('word_count', 0)}")
            print(f"      Quality: {sample_chunk.get('quality_score', 0):.2f}")
            print(f"      Keywords: {', '.join(sample_chunk.get('keywords', []))}")
            text_preview = sample_chunk.get('text_chunk', '')[:200]
            print(f"      Content: {text_preview}...")
        
        print(f"\n🎯 Overall Assessment:")
        if (poor_keyword_percentage < 30 and 
            avg_words >= 80 and 
            avg_quality >= 0.8):
            print("   🎉 QUALITY IS GOOD - Ready for indexing!")
        elif (poor_keyword_percentage < 50 and 
              avg_words >= 60 and 
              avg_quality >= 0.6):
            print("   ⚠️ QUALITY IS MODERATE - Consider further improvements")
        else:
            print("   ❌ QUALITY IS POOR - Needs significant improvement")
        
    except Exception as e:
        print(f"❌ Error analyzing quality file: {e}")


def main():
    """Main function to analyze existing quality files."""
    print("🔍 Quality Improvement Analysis")
    print("Looking for existing quality output files...")
    
    # Look for quality output files
    quality_dirs = [
        Path("quality_inspection_output"),
        Path("real_data_quality"),
        Path("quality_output"),
        Path("improved_quality_output"),
        Path("manual_quality_output")
    ]
    
    quality_files = []
    for quality_dir in quality_dirs:
        if quality_dir.exists():
            json_files = list(quality_dir.glob("processed_data_*.json"))
            quality_files.extend(json_files)
    
    if not quality_files:
        print("❌ No quality output files found!")
        print("   Run the pipeline first to generate quality files:")
        print("   python3 enhanced_pipeline_runner.py --batch-dir ../../RawHTMLdata --pattern 'batch_*.json'")
        return
    
    # Analyze the most recent quality file
    latest_file = max(quality_files, key=lambda f: f.stat().st_mtime)
    print(f"📁 Analyzing: {latest_file}")
    print()
    
    analyze_quality_file(latest_file)


if __name__ == "__main__":
    main()
