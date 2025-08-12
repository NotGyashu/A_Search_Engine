"""
Raw HTML Content Extractor

Handles the extraction of clean content and metadata from raw HTML using
optimized parsing libraries with fallback mechanisms.
"""

import logging
from typing import Optional, Dict, Any, List
from lxml import html as lxml_html
import trafilatura
from trafilatura import extract, extract_metadata
from trafilatura.settings import use_config

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
        # Configure trafilatura for optimal extraction
        self.config = use_config()
        self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
        self.config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "25")
        self.config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")
        self.config.set("DEFAULT", "INCLUDE_IMAGES", "False")
        self.config.set("DEFAULT", "DEDUPLICATE", "True")

         # Compile regex patterns
        self.api_pattern = re.compile(r'\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_]+\b')
        self.function_pattern = re.compile(r'\b[a-z_][a-z0-9_]*\(.*?\)\b')
        self.code_annotation_pattern = re.compile(r'#\s*<code>(.*?)<\/code>', re.DOTALL)

    
    def extract_content(self, html_content: str, url: str, raw_doc: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main content extraction method that processes HTML and returns structured data.
        
        Args:
            html_content: Raw HTML content
            url: Document URL
            raw_doc: Already extracted metadata from crawler (title, text_snippet, etc.)
        """
        # Initialize result with crawler data if available
        result = {
            'main_content': '',
            'title': raw_doc.get('title', '') if raw_doc else '',
            'description': raw_doc.get('text_snippet', '') if raw_doc else '',
            'author': '',
            'date': raw_doc.get('timestamp', '') if raw_doc else '',
            'domain': raw_doc.get('domain', '') if raw_doc else '',
            'headings': [],
            'links': [],
            'code_blocks': [],
            'content_type': 'unknown',
            'language': 'en',
            'metrics': {},
            'url': url,
            'is_technical': False
        }
        
        try:
            # Parse HTML only once
            lxml_tree = self.parse_html(html_content)
            if not lxml_tree:
                # If parsing fails, return what we have from crawler
                logger.warning(f"HTML parsing failed for {url}, using crawler data only")
                return result
            
             # Extract with technical enhancements
            extraction_result = self.extract_with_enhancements(lxml_tree, url)
            result.update(extraction_result)
            
            
            # Extract structural elements (these add value for search)
            result['headings'] = self.extract_headings(lxml_tree)
            result['links'] = self.extract_links(lxml_tree, url)
            
            # Determine content type and get metrics
            result['content_type'] = self.determine_content_type(
                result['main_content'], 
                result['headings'], 
                url
            )

            # Calculate metrics
            result['metrics'] = self.calculate_content_metrics(
                result['main_content'], 
                result['headings'],
                len(result['code_blocks'])
            )

            # Technical content flag
            result['is_technical'] = self.is_technical_content(
                result['main_content'], 
                result['headings']
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            return result
        
    def parse_html(self, html_content: str) -> Optional[Any]:
        """Parse HTML content into lxml tree with error handling."""
        try:
            return lxml_html.fromstring(html_content)
        except Exception as e:
            logger.warning(f"LXML parsing failed: {e}")
            return None
    
    def extract_with_enhancements(self, lxml_tree: Any, url: str) -> Dict[str, Any]:
        """Multi-stage extraction with technical content preservation."""
        result = {'main_content': '', 'code_blocks': []}
        
        # Pass 1: Extract with trafilatura (best for standard content)
        main_content = self.extract_main_content(lxml_tree)
        
        
        # Pass 2: Extract and preserve code blocks
        code_blocks = self.extract_code_blocks(lxml_tree)
        result['code_blocks'] = code_blocks
        
        # Pass 3: Enhanced extraction for technical content
        if not main_content or len(main_content) < 500:
            main_content = self.extract_technical_content(lxml_tree, url)
        
        # Pass 4: Fallback if all else fails
        if not main_content or len(main_content) < 300:
            main_content = self._extract_text_fallback(lxml_tree)
            
        # Annotate API references and function calls
        main_content = self.annotate_technical_references(main_content)
        
        # Reinsert code blocks as annotated blocks
        for i, block in enumerate(code_blocks):
            placeholder = f"\n# <code>CODE_BLOCK_{i}</code>\n"
            main_content = main_content.replace(block['text'], placeholder, 1)
        
        result['main_content'] = main_content
        return result
    
    def extract_main_content(self, lxml_tree: Any) -> Optional[str]:
        """Extract main content using trafilatura with enhanced settings."""
        try:
            content = extract(
                lxml_tree,
                include_comments=False,
                include_tables=True,  # Include tables for technical content
                include_links=False,
                no_fallback=False,  # Allow fallback for better coverage
                config=self.config
            )
            return content
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return None

    def extract_technical_content(self, lxml_tree: Any, url: str) -> str:
        """Specialized extraction for technical documentation."""
        content_parts = []
        
        # Extract by semantic sections
        sections = [
            ('//*[@id="overview"]',           "Overview"),
            ('//*[@id="introduction"]',       "Introduction"),
            ('//*[@id="installation"]',       "Installation"),
            ('//*[@id="requirements"]',       "Requirements"),
            ('//*[@id="setup"]',              "Setup"),
            ('//*[@id="getting-started"]',    "Getting Started"),
            ('//*[@id="usage"]',              "Usage"),
            ('//*[@id="configuration"]',      "Configuration"),
            ('//*[@id="options"]',            "Options"),
            ('//*[@id="parameters"]',         "Parameters"),
            ('//*[@id="properties"]',         "Properties"),
            ('//*[@id="methods"]',            "Methods"),
            ('//*[@id="functions"]',          "Functions"),
            ('//*[@id="endpoints"]',          "Endpoints"),
            ('//*[@id="examples"]',           "Examples"),
            ('//*[@id="code-examples"]',      "Code Examples"),
            ('//*[@id="responses"]',          "Responses"),
            ('//*[@id="return-values"]',      "Return Values"),
            ('//*[@id="errors"]',             "Errors"),
            ('//*[@id="exceptions"]',         "Exceptions"),
            ('//*[@id="events"]',             "Events"),
            ('//*[@id="notes"]',              "Notes"),
            ('//*[@id="faq"]',                "FAQ"),
            ('//*[@id="troubleshooting"]',    "Troubleshooting"),
            ('//*[@id="performance"]',        "Performance"),
            ('//*[@id="security"]',           "Security"),
            ('//*[@id="schema"]',             "Schema"),
            ('//*[@id="diagram"]',            "Diagram"),
            ('//article',                     "Article"),
            ('//main',                        "Main Content"),
            ('//section[contains(@class,"doc")]', "Doc Section"),
            ('//div[contains(@class,"content")]', "Content Block"),
        ]

        
        for xpath, section_name in sections:
            elements = lxml_tree.xpath(xpath)
            if elements:
                try:
                    section_text = elements[0].text_content().strip()
                    if section_text and len(section_text) > 100:
                        content_parts.append(f"\n\n### {section_name} ###\n\n")
                        content_parts.append(section_text)
                except Exception:
                    continue
        
        return "\n".join(content_parts) if content_parts else ""

    def extract_code_blocks(self, lxml_tree: Any) -> List[Dict[str, str]]:
        """Extract and preserve code blocks with language detection."""
        code_blocks = []
        
        # XPath to find code containers
        code_containers = lxml_tree.xpath('//pre|//code|//div[contains(@class, "code")]')
        
        for container in code_containers:
            try:
                # Get language from class attributes
                class_list = container.get('class', '').split()
                language = 'unknown'
                for cls in class_list:
                    if cls.startswith('language-'):
                        language = cls[9:]
                    elif cls in [
                            'python', 'js', 'javascript', 'java', 'c++', 'html', 'css',
                            'c', 'c#', 'php', 'ruby', 'go', 'rust', 'typescript', 'swift',
                            'kotlin', 'r', 'scala', 'perl', 'dart', 'matlab', 'sql', 'bash',
                            'objective-c', 'lua', 'groovy', 'haskell', 'elixir', 'erlang'
                        ]:
                        language = cls

                
                # Extract clean code text
                code_text = container.text_content().strip()
                if code_text and len(code_text) > 10:
                    code_blocks.append({
                        'text': code_text,
                        'language': language,
                        'element': container.tag
                    })
            except Exception as e:
                logger.debug(f"Code extraction failed: {e}")
                continue
        
        return code_blocks
    
    
    def _extract_text_fallback(self, lxml_tree: Any) -> str:
        """Fallback text extraction when trafilatura fails."""
        try:
            # Remove script and style elements
            for element in lxml_tree.xpath('.//script | .//style | .//nav | .//header | .//footer'):
                element.getparent().remove(element)
            
            # Get text from main content areas
            main_selectors = [
                './/main', './/article', './/div[@class*="content"]',
                './/div[@id*="content"]', './/div[@class*="post"]'
            ]
            
            for selector in main_selectors:
                elements = lxml_tree.xpath(selector)
                if elements:
                    text = elements[0].text_content()
                    if text and len(text.strip()) > 100:
                        return text.strip()
            
            # Final fallback: get all text
            return lxml_tree.text_content().strip()
            
        except Exception as e:
            logger.warning(f"Fallback text extraction failed: {e}")
            return ""
    
    def annotate_technical_references(self, content: str) -> str:
        """Annotate API references and function calls in content."""
        # Annotate API references
        content = self.api_pattern.sub(r'# <api>\g<0></api>', content)
        
        # Annotate function calls
        content = self.function_pattern.sub(r'# <fn>\g<0></fn>', content)
        
        # Annotate technical keywords
        for phrase in self.TECHNICAL_KEYPHRASES:
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            content = pattern.sub(r'# <tech>\g<0></tech>', content)
        
        return content
    
    def extract_metadata(self, lxml_tree: Any) -> Dict[str, Optional[str]]:
        """Extract comprehensive metadata from HTML."""
        metadata = {
            'title': None,
            'description': None,
            'author': None,
            'date': None,
            'sitename': None,
            'language': None
        }
        
        try:
            meta = extract_metadata(lxml_tree)
            if meta:
                metadata.update({
                    'title': meta.title,
                    'description': meta.description,
                    'author': meta.author,
                    'date': meta.date,
                    'sitename': meta.sitename,
                    'language': meta.language
                })
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
        
        # Fallback extraction for critical fields
        if not metadata['title']:
            metadata['title'] = self._extract_title_fallback(lxml_tree)
        
        if not metadata['description']:
            metadata['description'] = self._extract_description_fallback(lxml_tree)
            
        return metadata
    
    def _extract_title_fallback(self, lxml_tree: Any) -> Optional[str]:
        """Fallback title extraction using multiple strategies."""
        try:
            # Strategy 1: H1 tags (often more specific than <title>)
            h1_elements = lxml_tree.xpath('.//h1')
            if h1_elements:
                h1_text = h1_elements[0].text_content().strip()
                if h1_text and len(h1_text) > 5:
                    return h1_text
            
            # Strategy 2: Title tag
            title_elements = lxml_tree.xpath('.//title')
            if title_elements:
                title_text = title_elements[0].text_content().strip()
                if title_text:
                    return title_text
            
            # Strategy 3: Meta property og:title
            og_title = lxml_tree.xpath('.//meta[@property="og:title"]/@content')
            if og_title:
                return og_title[0].strip()
            
            # Strategy 4: First meaningful heading
            for level in ['h2', 'h3']:
                headings = lxml_tree.xpath(f'.//{level}')
                if headings:
                    heading_text = headings[0].text_content().strip()
                    if heading_text and len(heading_text) > 5:
                        return heading_text
                        
        except Exception as e:
            logger.warning(f"Title fallback extraction failed: {e}")
        
        return None
    
    def _extract_description_fallback(self, lxml_tree: Any) -> Optional[str]:
        """Fallback description extraction."""
        try:
            # Meta description
            meta_desc = lxml_tree.xpath('.//meta[@name="description"]/@content')
            if meta_desc:
                return meta_desc[0].strip()
            
            # Open Graph description
            og_desc = lxml_tree.xpath('.//meta[@property="og:description"]/@content')
            if og_desc:
                return og_desc[0].strip()
            
            # First paragraph
            paragraphs = lxml_tree.xpath('.//p')
            for p in paragraphs:
                p_text = p.text_content().strip()
                if p_text and len(p_text) > 50:
                    return p_text[:300]
                    
        except Exception as e:
            logger.warning(f"Description fallback extraction failed: {e}")
        
        return None
    
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
    
    def detect_content_type(self, url: str, content: str) -> str:
        """Detect the type of content (article, tutorial, documentation, etc.)."""

        url_lower = url.lower()
        content_lower = content.lower()

        # 1) URL-based patterns
        URL_PATTERNS = {
            'documentation': [
                '/docs/', '/documentation/', '/reference/', '/spec/', '/api/', 
                '/swagger/', '/openapi/', '/developer-guide/', '/manual/', '/guide/'
            ],
            'tutorial': [
                '/tutorials/', '/how-to/', '/getting-started/', '/walkthrough/', 
                '/examples/', '/step-by-step/'
            ],
            'blog': [
                '/blog/', '/articles/', '/posts/', '/news/', '/stories/', '/insights/'
            ],
            'api_reference': [
                '/api/', '/reference/', '/v1/', '/v2/', '/rest/', '/graphql/'
            ],
            'news': [
                '/news/', '/press-release/', '/updates/', '/announcements/'
            ],
        }

        for ctype, patterns in URL_PATTERNS.items():
            if any(seg in url_lower for seg in patterns):
                return ctype

        # 2) Content-based keywords
        CONTENT_KEYWORDS = {
            'documentation': {
                'api', 'documentation', 'reference', 'guide', 'manual', 'specification',
                'doc', 'docs', 'developer guide', 'sdk', 'architecture'
            },
            'tutorial': {
                'tutorial', 'how to', 'step by step', 'walkthrough', 'beginner',
                'getting started', 'example', 'demo', 'exercise'
            },
            'news': {
                'breaking', 'news', 'today', 'yesterday', 'reported', 'announced',
                'press release', 'update', 'latest'
            },
            'blog': {
                'blog', 'posted by', 'author:', 'published', 'post', 'entry', 'insights',
                'opinion', 'weblog'
            },
            'api_reference': {
                'endpoint', 'request', 'response', 'http', 'status code', 'path param',
                'query param', 'header', 'body', 'payload', 'rate limit'
            }
        }

        # scan content once
        for ctype, keywords in CONTENT_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                return ctype

        # 3) Fallback default
        return 'article'

    
    def determine_content_type(self, main_content: str, metadata: Dict[str, Any], headings: List[Dict[str, Any]]) -> str:
        """Determine content type based on content analysis."""
        return self.detect_content_type(None, main_content)
    

    def is_technical_content(self, content: str, headings: List[Dict]) -> bool:
        """Determine if content is technical."""
        if not content:
            return False
            
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
        heading_text = " ".join(h['text'] for h in headings).lower()
        if any(kw in heading_text for kw in tech_keywords):
            return True
            
        # Check for code annotations
        if '# <code>' in content or '# <api>' in content or '# <fn>' in content:
            return True
            
        return False
    

    def calculate_content_metrics(self, content: str, headings: List[Dict] = None) -> Dict[str, Any]:
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
    