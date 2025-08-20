"""
Raw HTML Content Extractor

Handles the extraction of clean content and metadata from raw HTML using
optimized parsing libraries with fallback mechanisms.
"""

import logging
import re
import warnings
from typing import Optional, Dict, Any, List
from lxml import html as lxml_html
import trafilatura
from trafilatura import extract
from trafilatura.settings import use_config

# Suppress trafilatura warnings for cleaner logs
trafilatura_logger = logging.getLogger('trafilatura')
trafilatura_logger.setLevel(logging.ERROR)
warnings.filterwarnings("ignore", module="trafilatura")

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Advanced HTML content extraction with multiple strategies."""
    
    # HTML tags to preserve as-is in extraction
    PRESERVE_TAGS = {'pre', 'code', 'kbd', 'samp', 'var'}
    
    # Technical content indicators
    TECHNICAL_KEYPHRASES = [
        'api', 'function', 'class', 'method', 'property', 'parameter',
        'returns', 'throws', 'example', 'syntax', 'interface', 'implementation'
    ]

    def __init__(self):
        # Configure trafilatura for optimal extraction with more lenient settings
        self.config = use_config()
        self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        self.config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "10")  # More lenient
        self.config.set("DEFAULT", "MIN_OUTPUT_SIZE", "50")     # More lenient
        self.config.set("DEFAULT", "INCLUDE_IMAGES", "False")
        self.config.set("DEFAULT", "DEDUPLICATE", "True")
        self.config.set("DEFAULT", "FAVOR_PRECISION", "False")  # More content extraction
        self.config.set("DEFAULT", "FAVOR_RECALL", "True")      # Better coverage

        # Compile regex patterns once for reuse (optimized)
        self.api_pattern = re.compile(r'\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_]+\b')
        self.function_pattern = re.compile(r'\b[a-z_][a-z0-9_]*\(.*?\)\b')
        
        # Combined technical annotation pattern (more efficient)
        tech_keywords = '|'.join(re.escape(kw) for kw in self.TECHNICAL_KEYPHRASES)
        self.tech_pattern = re.compile(rf'\b(?:{tech_keywords})\b', re.IGNORECASE)
        
        # Cache for parsed trees
        self._tree_cache = {}

    
    def extract_content(self, html_content: str, url: str, raw_doc: Dict[str, Any] = None, soup=None) -> Dict[str, Any]:
        """Streamlined content extraction method - optimized for performance."""
        result = {
            'main_content': ''
            
        }

        try:
            # Use cached parsed tree if available
            if soup is not None:
                # Convert soup to lxml tree once and cache
                cache_key = hash(str(soup)[:1000])  # Use hash of first 1KB as cache key
                if cache_key not in self._tree_cache:
                    lxml_tree = lxml_html.fromstring(str(soup))
                    self._clean_tree_elements(lxml_tree)  # Use lxml-based cleaning
                    self._tree_cache[cache_key] = lxml_tree
                lxml_tree = self._tree_cache[cache_key]
            else:
                lxml_tree = self.parse_html(html_content)

            if lxml_tree is None:
                # Single fallback attempt with trafilatura
                main_content = extract(html_content, config=self.config)
                if main_content:
                    result['main_content'] = self.annotate_technical_references(main_content)
                return result

            # Single-pass extraction (no multiple fallbacks)
            main_content = self.extract_main_content(lxml_tree)
            
            # Only try technical extraction if main content is very short
            if not main_content or len(main_content) < 200:
                main_content = self.extract_technical_content(lxml_tree, url)
            
            # Annotate technical references once
            if main_content:
                result['main_content'] = self.annotate_technical_references(main_content)

            return result

        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            return result

        
    def parse_html(self, html_content: str) -> Optional[Any]:
        """Parse HTML content into lxml tree with efficient element-based cleaning."""
        try:
            # Parse HTML first
            tree = lxml_html.fromstring(html_content)
            # Clean using lxml operations (much faster than regex)
            self._clean_tree_elements(tree)
            return tree
        except Exception as e:
            logger.warning(f"LXML parsing failed: {e}")
            return None
    
    def _clean_tree_elements(self, tree) -> None:
        """Efficiently remove unwanted elements using lxml operations."""
        # Remove scripts, styles, and other unwanted elements in one pass
        unwanted_tags = ['script', 'style', 'noscript', 'iframe', 'embed', 'object']
        for tag in unwanted_tags:
            for element in tree.xpath(f'.//{tag}'):
                if element.getparent() is not None:
                    element.getparent().remove(element)
    
    # Multi-stage extraction removed - replaced with streamlined single-pass extraction
    
    def extract_main_content(self, lxml_tree: Any) -> Optional[str]:
        """Extract main content using trafilatura with enhanced settings."""
        try:
            # Convert lxml tree back to string for trafilatura
            html_str = lxml_html.tostring(lxml_tree, encoding='unicode')
            
            # Temporarily suppress trafilatura warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                content = extract(
                    html_str,
                    include_comments=False,
                    include_tables=True,  # Include tables for technical content
                    include_links=False,
                    no_fallback=False,  # Allow fallback for better coverage
                    config=self.config
                )
            
            # Return content or None silently if extraction failed
            return content if content and len(content.strip()) > 0 else None
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return None

    def extract_technical_content(self, lxml_tree: Any, url: str) -> str:
        """Simplified technical content extraction with batched XPath queries."""
        content_parts = []
        
        # Batch XPath queries for better performance
        all_selectors = [
            '//article', '//main', '//section[contains(@class,"doc")]', 
            '//div[contains(@class,"content")]', '//*[@id="overview"]',
            '//*[@id="introduction"]', '//*[@id="usage"]', '//*[@id="examples"]'
        ]
        
        # Single XPath query for all selectors
        xpath_query = ' | '.join(all_selectors)
        elements = lxml_tree.xpath(xpath_query)
        
        for element in elements[:5]:  # Limit to first 5 matches for performance
            try:
                section_text = element.text_content().strip()
                if section_text and len(section_text) > 100:
                    content_parts.append(section_text)
                    if len(' '.join(content_parts)) > 2000:  # Stop when we have enough content
                        break
            except Exception:
                continue
        
        return "\n\n".join(content_parts[:3]) if content_parts else ""  # Limit output size

    # Code block extraction removed per user request for performance optimization
    
    
    # Fallback text extraction removed - using single-pass extraction approach for performance
    
    def annotate_technical_references(self, content: str) -> str:
        """Optimized technical reference annotation using combined patterns."""
        if not content or len(content) > 50000:  # Skip very large content for performance
            return content
        
        # Single-pass annotation with combined patterns (more efficient)
        # Annotate API references
        content = self.api_pattern.sub(r'# <api>\g<0></api>', content)
        
        # Annotate function calls  
        content = self.function_pattern.sub(r'# <fn>\g<0></fn>', content)
        
        # Annotate technical keywords in one pass
        content = self.tech_pattern.sub(r'# <tech>\g<0></tech>', content)
        
        return content
    
    def extract_headings(self, lxml_tree: Any) -> list:
        """Extract structured headings with hierarchy."""
        headings = []
        try:
            # Extract headings with level information
            for level in range(1, 7):  # h1 to h6
                elements = lxml_tree.xpath(f'.//h{level}')
                for elem in elements:
                    text = elem.text_content().strip()
                    if text and len(text) > 2:  # Filter out very short headings
                        headings.append({
                            'level': level,
                            'text': text,
                            'id': elem.get('id', ''),
                            'class': elem.get('class', '')
                        })
        except Exception as e:
            logger.warning(f"Headings extraction failed: {e}")
        
        return headings
    
    def extract_links(self, lxml_tree: Any, base_url: str = "") -> list:
        """Extract internal and external links."""
        links = []
        try:
            link_elements = lxml_tree.xpath('.//a[@href]')
            for link in link_elements:
                href = link.get('href', '').strip()
                text = link.text_content().strip()
                
                if href and text:
                    links.append({
                        'url': href,
                        'text': text,
                        'is_external': href.startswith(('http://', 'https://'))
                    })
        except Exception as e:
            logger.warning(f"Links extraction failed: {e}")
        
        return links
    
    def is_technical_content(self, content: str, headings: List[Dict]) -> bool:
        """Determine if content is technical."""
        if not content:
            return False
        
        content_lower = content.lower()
            
        tech_keywords = [
            # Core programming & CS
            'api', 'function', 'method', 'parameter', 'interface', 'implementation',
            'algorithm', 'array', 'binary', 'cache', 'compiler', 'concurrency', 'container',
            'database', 'debug', 'encryption', 'framework', 'frontend', 'backend',
            'hash', 'inheritance', 'instance', 'iteration', 'json', 'kernel', 'middleware',
            'microservice', 'module', 'namespace', 'network', 'object', 'operator',
            'query', 'queue', 'recursive', 'repository', 'runtime', 'scalability', 'schema', 'script',
            'serialization', 'sdk', 'service', 'session', 'stack', 'stream', 'syntax', 'thread',
            'token', 'url', 'validation', 'virtual', 'volatile', 'websocket', 'xml', 'yaml',
            'buffer', 'bytecode', 'cli', 'cluster', 'docker', 'gateway', 'host', 'index', 'latency',
            'mutex', 'node', 'router', 'ssl', 'tcp', 'udp', 'ux', 'vm',

            # Machine Learning & Data
            'ai', 'machine learning', 'deep learning', 'neural', 'neuron', 'tensor', 'regression',
            'classification', 'clustering', 'random forest', 'gradient boosting', 'svm', 'knn',
            'cnn', 'rnn', 'transformer', 'attention', 'nlp', 'computer vision', 'feature', 'label',
            'training', 'inference', 'overfitting', 'underfitting', 'cross validation',
            'hyperparameter',  'optimizer', 'backpropagation', 'epoch', 'dataset',
            'pipeline', 'preprocessing', 'augmentation', 'embedding', 'vector', 'pytorch', 'tensorflow',
            'keras', 'sklearn', 'xgboost', 'lightgbm',

            # Trending technologies
            'blockchain', 'smart contract', 'web3', 'metaverse', 'iot', 'edge computing',
            'serverless', 'kubernetes', 'helm', 'istio', 'service mesh', 'graphql', 'observability',
            'prometheus', 'grafana', 'ci/cd', 'devops', 'gitops', 'terraform', 'ansible',
            'chaos engineering', 'blockchain', 'defi', 'nft', 'quantum computing', '5g',
            'augmented reality', 'virtual reality', 'digital twin', 'microfrontend', 'edge ai'
        ]

        
        if any(kw in content_lower for kw in tech_keywords):
            return True
            
        # Check headings for technical terms
        if headings:
            heading_text = " ".join(h.get('text', '') for h in headings if h.get('text')).lower()
            if any(kw in heading_text for kw in tech_keywords):
                return True
            
        # Check for code annotations
        if '# <code>' in content or '# <api>' in content or '# <fn>' in content:
            return True
            
        return False
    

    def calculate_content_metrics(self, content: str, headings: List[Dict] = None, code_blocks_count: int = 0) -> Dict[str, Any]:
        """Calculate various content metrics for quality assessment."""
        if not content:
            return {}
        
        try:
            words = content.split()
            sentences = content.split('.')
            paragraphs = content.split('\n\n')
            
            return {
                'word_count': len(words),
                'sentence_count': len([s for s in sentences if s.strip()]),
                'paragraph_count': len([p for p in paragraphs if p.strip()]),
                'avg_sentence_length': len(words) / max(len(sentences), 1),
                'reading_time_minutes': len(words) / 200,  # Assume 200 WPM
                'heading_count': len(headings) if headings else 0,
                'content_density': len(content.replace(' ', '')) / max(len(content), 1)
            }
        except Exception as e:
            logger.warning(f"Content metrics calculation failed: {e}")
            return {}
    