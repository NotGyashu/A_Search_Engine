# Document Processing Pipeline - Cost Optimized
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import html2text
from typing import List, Dict, Tuple
import hashlib

class CostOptimizedProcessor:
    def __init__(self):
        self.h = html2text.HTML2Text()
        self.h.ignore_links = True
        self.h.ignore_images = True
        self.max_chunk_size = 2000  # Optimal for embedding models
        
    def extract_clean_text(self, html_content: str) -> str:
        """Extract clean text from HTML, removing noise"""
        # Remove script, style, nav, footer, ads
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
            
        # Extract main content areas
        main_content = soup.find(['main', 'article', 'div[class*="content"]']) or soup
        
        # Convert to clean text
        text = self.h.handle(str(main_content))
        
        # Clean up
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove extra newlines
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)  # Remove special chars
        
        return text.strip()
    
    def chunk_text(self, text: str, url: str) -> List[Dict]:
        """Split text into optimal chunks for processing"""
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '. '.join(current_chunk) + '.'
                chunks.append({
                    'url': url,
                    'text': chunk_text,
                    'size': current_size,
                    'chunk_id': hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                })
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = '. '.join(current_chunk) + '.'
            chunks.append({
                'url': url,
                'text': chunk_text,
                'size': current_size,
                'chunk_id': hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            })
        
        return chunks
    
    def process_crawler_batch(self, batch_file: Path) -> List[Dict]:
        """Process a single crawler batch file efficiently"""
        print(f"Processing {batch_file.name}...")
        
        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)
        
        processed_chunks = []
        
        for item in batch_data:
            url = item.get('url', '')
            html = item.get('content', '')
            
            # Skip if too small or too large
            if len(html) < 500 or len(html) > 2_000_000:
                continue
            
            # Extract clean text
            clean_text = self.extract_clean_text(html)
            
            # Skip if extracted text is too small
            if len(clean_text) < 200:
                continue
            
            # Create chunks
            chunks = self.chunk_text(clean_text, url)
            processed_chunks.extend(chunks)
        
        return processed_chunks

# Cost calculation helper
def estimate_processing_cost(total_tokens: int, model: str = "gpt-3.5-turbo") -> float:
    """Estimate cost for processing"""
    costs = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},  # per 1K tokens
        "gpt-4": {"input": 0.03, "output": 0.06},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }
    
    # Assume 1:2 input to output ratio
    input_tokens = total_tokens * 0.67
    output_tokens = total_tokens * 0.33
    
    cost = costs[model]
    total_cost = (input_tokens / 1000 * cost["input"]) + (output_tokens / 1000 * cost["output"])
    
    return total_cost

if __name__ == "__main__":
    processor = CostOptimizedProcessor()
    
    # Example: Process your crawler data
    data_dir = Path("../data/raw")
    batch_files = list(data_dir.glob("batch_*.json"))
    
    total_chunks = 0
    total_tokens = 0
    
    for batch_file in batch_files[:3]:  # Process first 3 files as example
        chunks = processor.process_crawler_batch(batch_file)
        total_chunks += len(chunks)
        total_tokens += sum(len(chunk['text'].split()) * 1.3 for chunk in chunks)  # Rough token estimate
    
    print(f"\nProcessing Summary:")
    print(f"Total chunks: {total_chunks}")
    print(f"Estimated tokens: {total_tokens:,.0f}")
    print(f"Cost with GPT-3.5-turbo: ${estimate_processing_cost(total_tokens, 'gpt-3.5-turbo'):.2f}")
    print(f"Cost with Claude Haiku: ${estimate_processing_cost(total_tokens, 'claude-3-haiku'):.2f}")
