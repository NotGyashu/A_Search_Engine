# Document Processing Pipeline - Cost Optimized (with saving & preview)
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import html2text
from typing import List, Dict
import hashlib


class CostOptimizedProcessor:
    def __init__(self):
        self.h = html2text.HTML2Text()
        self.h.ignore_links = True
        self.h.ignore_images = True
        self.max_chunk_size = 2000  # Optimal for embedding models

    def extract_clean_text(self, html_content: str) -> str:
        """Extract clean text from HTML, removing noise"""
        soup = BeautifulSoup(html_content, 'html.parser')

        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        main_content = soup.find(['main', 'article', 'div[class*="content"]']) or soup
        text = self.h.handle(str(main_content))

        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
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
        print(f"📦 Processing {batch_file.name}...")

        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)

        processed_chunks = []

        for item in batch_data:
            url = item.get('url', '')
            html = item.get('content', '')

            if len(html) < 500 or len(html) > 2_000_000:
                continue

            clean_text = self.extract_clean_text(html)

            if len(clean_text) < 200:
                continue

            chunks = self.chunk_text(clean_text, url)
            processed_chunks.extend(chunks)

        return processed_chunks


# Cost calculation helper
def estimate_processing_cost(total_tokens: int, model: str = "gpt-3.5-turbo") -> float:
    costs = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }

    input_tokens = total_tokens * 0.67
    output_tokens = total_tokens * 0.33

    cost = costs[model]
    total_cost = (input_tokens / 1000 * cost["input"]) + (output_tokens / 1000 * cost["output"])
    return total_cost


if __name__ == "__main__":
    processor = CostOptimizedProcessor()

    data_dir = Path("../../RawHTMLdata")
    output_dir = Path("../../ProcessedChunks")
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_files = list(data_dir.glob("batch_*.json"))

    total_chunks = 0
    total_tokens = 0

    for i, batch_file in enumerate(batch_files[:3]):  # First 3 files
        chunks = processor.process_crawler_batch(batch_file)
        total_chunks += len(chunks)
        total_tokens += sum(len(chunk['text'].split()) * 1.3 for chunk in chunks)

        # Save processed chunks
        output_file = output_dir / f"cleaned_{batch_file.name}"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved {len(chunks)} cleaned chunks to {output_file}")

        # Optional: preview first few chunks
        print("\n🔍 Previewing first 3 chunks:")
        for chunk in chunks[:3]:
            print(f"\n🔗 URL: {chunk['url']}")
            print(f"🧾 Text:\n{chunk['text'][:800]}")  # Preview up to 800 characters
            print("=" * 60)

    print(f"\n📊 Summary:")
    print(f"Total chunks: {total_chunks}")
    print(f"Estimated tokens: {total_tokens:,.0f}")
    print(f"💰 GPT-3.5 cost: ${estimate_processing_cost(total_tokens, 'gpt-3.5-turbo'):.2f}")
    print(f"💰 Claude Haiku cost: ${estimate_processing_cost(total_tokens, 'claude-3-haiku'):.2f}")
