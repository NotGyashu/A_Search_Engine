use std::collections::HashMap;
use tl::{Parser, HTMLTag, Node};
use regex::Regex;
use chrono::{DateTime, NaiveDateTime, Utc, TimeZone, NaiveDate};
use crate::types::*;
use crate::cleaner::FastCleaner;

pub struct OptimizedExtractor {
    // Precompiled regex patterns for performance
    api_pattern: Regex,
    function_pattern: Regex,
    tech_pattern: Regex,
    date_patterns: Vec<Regex>,
    url_pattern: Regex,
    email_pattern: Regex,
}

impl OptimizedExtractor {
    pub fn new() -> Self {
        // Technical content patterns (reduced for performance)
        let tech_keywords = [
            "api", "function", "class", "method", "algorithm", "code", "software", 
            "programming", "development", "technology", "technical", "system", 
            "framework", "library", "database", "server", "client", "frontend", "backend", 
            "fullstack", "compiler", "interpreter", "object", "variable", "loop", 
            "conditional", "array", "string", "boolean", "integer", "float", "pointer", 
            "recursion", "stack", "queue", "tree", "graph", "hash", "encryption", 
            "protocol", "network", "cloud", "virtualization", "container", "docker", 
            "kubernetes", "ci", "cd", "git", "version", "control", "repository", 
            "branch", "merge", "commit", "pull", "push", "debug", "exception", 
            "error", "log", "performance", "optimization", "testing", "unit", "integration", 
            "api-testing", "endpoint", "request", "response", "json", "xml", "yaml", 
            "html", "css", "javascript", "typescript", "python", "java", "c++", "c#", 
            "ruby", "php", "sql", "nosql", "mongodb", "postgresql", "mysql", "algorithmic", 
            "data", "datastructure", "machine-learning", "ai", "artificial-intelligence", 
            "deep-learning", "neural-network", "automation", "script", "shell", 
            "bash", "powershell", "devops", "security", "authentication", "authorization", 
            "token", "session", "cookie", "ssl", "tls", "http", "https", "rest", 
            "graphql", "websocket", "middleware", "architecture", "design-pattern", 
            "microservice", "singleton", "observer", "factory", "adapter", "decorator", 
            "strategy", "prototype", "thread", "process", "concurrency", "asynchronous", 
            "synchronous", "event-driven", "callback", "promise", "lambda", "api-gateway",
            "load-balancer", "cache", "cdn", "elastic", "scalability", "availability", 
            "redundancy", "backup", "replication", "cluster", "sharding", "indexing", 
            "query", "optimization", "latency", "throughput", "bandwidth", "iot", 
            "edge-computing", "serverless", "function-as-a-service", "infrastructure", 
            "monitoring", "logging", "tracing", "alerting", "incident", "sla", "slo", 
            "ci-cd-pipeline", "orchestration", "automation-script", "virtual-machine", 
            "hypervisor", "sandbox", "debugging-tool", "profiling", "refactoring", 
            "code-review", "linting", "formatter", "build-tool", "package-manager", 
            "dependency", "versioning", "semantic-versioning", "sdk", "ide", "terminal", 
            "cli", "restful", "crud", "orm", "mvc", "mvvm", "repository-pattern", 
            "event-sourcing", "queueing", "messaging", "pub-sub", "observer-pattern", 
            "factory-pattern", "adapter-pattern", "strategy-pattern", "singleton-pattern",
            "decorator-pattern", "proxy-pattern", "facade-pattern", "bridge-pattern", 
            "composite-pattern", "flyweight-pattern", "iterator-pattern", "state-pattern", 
            "chain-of-responsibility", "command-pattern", "mediator-pattern", "memento-pattern",
            "prototype-pattern", "visitor-pattern", "dependency-injection", "inversion-of-control",
            "oop", "functional-programming", "procedural", "imperative", "declarative", 
            "multi-threading", "parallel-processing", "gpu-computing", "tensor", 
            "backpropagation", "cnn", "rnn", "lstm", "gan", "transformer", 
            "nlp", "computer-vision", "reinforcement-learning", "data-pipeline", 
            "etl", "data-warehouse", "data-lake", "big-data", "hadoop", "spark", 
            "flink", "kafka", "streaming", "batch-processing", "map-reduce"
        ];

        
        let tech_pattern_str = tech_keywords.join("|");
        
        // Essential date patterns only
        let date_patterns = vec![
            Regex::new(r"\d{4}-\d{2}-\d{2}").unwrap(),       // YYYY-MM-DD
            Regex::new(r"\d{2}/\d{2}/\d{4}").unwrap(),       // MM/DD/YYYY
            Regex::new(r"\d{2}-\d{2}-\d{4}").unwrap(),       // MM-DD-YYYY
            Regex::new(r"\d{2}\.\d{2}\.\d{4}").unwrap(),     // DD.MM.YYYY
            Regex::new(r"\d{4}/\d{2}/\d{2}").unwrap(),       // YYYY/MM/DD
            Regex::new(r"\d{4}\.\d{2}\.\d{2}").unwrap(),     // YYYY.MM.DD
            Regex::new(r"\d{2} \w+ \d{4}").unwrap(),         // DD Month YYYY (e.g., 25 August 2025)
            Regex::new(r"\w+ \d{2}, \d{4}").unwrap(),        // Month DD, YYYY (e.g., August 25, 2025)
            Regex::new(r"\d{1,2}/\d{1,2}/\d{2}").unwrap(),   // M/D/YY or MM/DD/YY
            Regex::new(r"\d{1,2}-\d{1,2}-\d{2}").unwrap(),   // M-D-YY or MM-DD-YY
            Regex::new(r"\d{1,2} \w{3} \d{4}").unwrap(),     // DD Mon YYYY (e.g., 25 Aug 2025)
            Regex::new(r"\d{1,2}-\w{3}-\d{4}").unwrap(),     // DD-Mon-YYYY (e.g., 25-Aug-2025)
            Regex::new(r"\w{3} \d{1,2}, \d{4}").unwrap(),    // Mon DD, YYYY (e.g., Aug 25, 2025)
            Regex::new(r"\d{8}").unwrap(),                   // YYYYMMDD
            Regex::new(r"\d{2}\s?/\s?\d{2}\s?/\s?\d{4}").unwrap(), // MM / DD / YYYY with optional spaces
        ];

        Self {
            api_pattern: Regex::new(r"\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_]+\b").unwrap(),
            function_pattern: Regex::new(r"\b[a-z_][a-z0-9_]*\(.*?\)\b").unwrap(),
            tech_pattern: Regex::new(&format!(r"(?i)\b(?:{})\b", tech_pattern_str)).unwrap(),
            date_patterns,
            url_pattern: Regex::new(r"https?://[^\s]+").unwrap(),
            email_pattern: Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap(),
        }
    }

    pub fn extract_content(&self, html: &str, base_url: &str) -> ProcessedDocument {
        let dom = tl::parse(html, tl::ParserOptions::default()).unwrap();
        let parser = dom.parser();
        
        let mut document = ProcessedDocument::default();
        
        // Extract essential metadata only
        self.extract_essential_metadata(&dom, parser, &mut document, base_url);
        
        // Extract and clean main content
        let raw_content = self.extract_main_content(&dom, parser);
        document.main_content = self.annotate_technical_content(&raw_content);
        
        // Generate keywords from content if no meta keywords found
        if document.keywords.is_empty() {
            document.keywords = self.extract_keywords_from_content(&document.main_content, 10);
        }
        
        // Create optimized chunks with context
        document.text_chunks_with_context = self.create_chunks_with_context(&document.main_content, &document.headings);
        
        // Calculate essential metrics only
        self.calculate_essential_metrics(&mut document);
        
        // Detect technical content
        document.is_technical_content = self.is_technical_content(&document);
        
        document
    }

    fn extract_essential_metadata(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
        // Extract title
        if let Some(title_node) = dom.query_selector("title").and_then(|mut iter| iter.next()) {
            if let Some(title_element) = title_node.get(parser) {
                document.title = title_element.inner_text(parser).trim().to_string();
            }
        }
        
        // Extract language
        if let Some(html_node) = dom.query_selector("html").and_then(|mut iter| iter.next()) {
            if let Some(html_element) = html_node.get(parser) {
                if let Some(HTMLTag { .. }) = html_element.as_tag() {
                    let attrs = html_element.as_tag().unwrap().attributes();
                    if let Some(lang) = attrs.get("lang").flatten() {
                        document.language = lang.as_utf8_str().to_string();
                    }
                }
            }
        }
        
        // Extract essential meta tags only
        self.extract_essential_meta_tags(dom, parser, document);
        
        // Extract essential structured data only
        self.extract_essential_structured_data(dom, parser, document);
        
        // Extract headings for content structure
        self.extract_headings(dom, parser, document);
        
        // Extract only primary image and favicon
        self.extract_essential_images(dom, parser, document, base_url);
        
        // Extract simplified author information
        self.extract_essential_author_info(dom, parser, document);
        
        // Extract publication dates
        self.extract_publication_dates(dom, parser, document);
        
        // Only extract canonical URL if different from base URL
        self.extract_canonical_url_if_different(dom, parser, document, base_url);
    }

    fn extract_essential_meta_tags(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        if let Some(meta_nodes) = dom.query_selector("meta") {
            for node_handle in meta_nodes {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attrs = tag.attributes();
                        
                        // Only extract essential meta tags
                        if let (Some(name), Some(content)) = (attrs.get("name").flatten(), attrs.get("content").flatten()) {
                            let name_str = name.as_utf8_str().to_lowercase();
                            let content_str = content.as_utf8_str().to_string();
                            
                            match name_str.as_str() {
                                "description" => document.description = content_str,
                                "keywords" => {
                                    document.keywords = content_str
                                        .split(',')
                                        .map(|k| k.trim().to_string())
                                        .filter(|k| !k.is_empty() && k.len() >= 3)
                                        .take(10) // Limit to 10 keywords
                                        .collect();
                                }
                                "author" => document.author_name = Some(content_str),
                                _ => {} // Ignore other meta tags
                            }
                        }
                    }
                }
            }
        }
    }

    fn extract_essential_structured_data(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        let mut structured_meta = StructuredMeta {
            article_type: None,
            featured_image: None,
            date_published: None,
            date_modified: None,
            publisher_name: None,
        };

        // Extract only essential data from JSON-LD
        if let Some(script_nodes) = dom.query_selector("script[type*='ld+json'], script[type*='application/ld+json']") {
            for node_handle in script_nodes {
                if let Some(node) = node_handle.get(parser) {
                    let script_content = node.inner_text(parser);
                    if let Ok(json_value) = serde_json::from_str::<serde_json::Value>(&script_content) {
                        self.extract_essential_from_json_ld(&json_value, &mut structured_meta);
                    }
                }
            }
        }

        // Only store if we found useful data
        if structured_meta.article_type.is_some() || 
           structured_meta.featured_image.is_some() || 
           structured_meta.publisher_name.is_some() {
            document.structured_meta = Some(structured_meta);
        }
    }

    fn extract_headings(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        for level in 1..=6 {
            let selector = format!("h{}", level);
            if let Some(heading_nodes) = dom.query_selector(&selector) {
                for node_handle in heading_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        let text = node.inner_text(parser).trim().to_string();
                        if !text.is_empty() && text.len() < 200 {
                            let heading = Heading {
                                level: level as u8,
                                text,
                            };
                            document.headings.push(heading);
                        }
                    }
                }
            }
        }
    }

    fn extract_essential_images(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
        // Look for primary/featured image first (og:image)
        if let Some(og_image) = dom.query_selector("meta[property='og:image']").and_then(|mut iter| iter.next()) {
            if let Some(node) = og_image.get(parser) {
                if let Some(tag) = node.as_tag() {
                    if let Some(content) = tag.attributes().get("content").flatten() {
                        let src = content.as_utf8_str().to_string();
                        document.primary_image = Some(ImageInfo {
                            src: self.resolve_url(&src, base_url),
                            alt: "Featured image".to_string(),
                        });
                    }
                }
            }
        }

        // If no og:image, look for the first meaningful img tag
        if document.primary_image.is_none() {
            if let Some(img_nodes) = dom.query_selector("img[src]") {
                for node_handle in img_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        if let Some(tag) = node.as_tag() {
                            let attrs = tag.attributes();
                            if let Some(src) = attrs.get("src").flatten() {
                                let src_str = src.as_utf8_str();
                                // Skip small icons and decorative images
                                if !src_str.contains("icon") && !src_str.contains("logo") && !src_str.contains("favicon") {
                                    let alt = attrs.get("alt").flatten()
                                        .map(|a| a.as_utf8_str().to_string())
                                        .unwrap_or_default();
                                    
                                    document.primary_image = Some(ImageInfo {
                                        src: self.resolve_url(&src_str, base_url),
                                        alt,
                                    });
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }

        // Extract favicon only
        if let Some(favicon_node) = dom.query_selector("link[rel*='icon']").and_then(|mut iter| iter.next()) {
            if let Some(node) = favicon_node.get(parser) {
                if let Some(tag) = node.as_tag() {
                    if let Some(href) = tag.attributes().get("href").flatten() {
                        document.favicon = Some(self.resolve_url(&href.as_utf8_str(), base_url));
                    }
                }
            }
        }
    }

    fn extract_essential_author_info(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        // Only extract author name, not full bio/social links
        if document.author_name.is_none() {
            let author_selectors = [
                ".author-name", ".author", "[data-author]", ".byline .name"
            ];
            
            for selector in &author_selectors {
                if let Some(author_node) = dom.query_selector(selector).and_then(|mut iter| iter.next()) {
                    if let Some(node) = author_node.get(parser) {
                        let author_text = node.inner_text(parser).trim().to_string();
                        if !author_text.is_empty() && author_text.len() < 100 {
                            document.author_name = Some(author_text);
                            break;
                        }
                    }
                }
            }
        }
    }

    fn extract_publication_dates(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        // Check meta tags first (essential patterns only)
        let pub_date_keys = [
            "article:published_time", "datePublished", "date"
        ];
        
        for key in &pub_date_keys {
            if let Some(meta_node) = dom.query_selector(&format!("meta[property='{}'], meta[name='{}']", key, key))
                .and_then(|mut iter| iter.next()) {
                if let Some(node) = meta_node.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attrs = tag.attributes();
                        if let Some(content) = attrs.get("content").flatten() {
                            if let Some(normalized) = self.parse_date_string(&content.as_utf8_str()) {
                                document.published_date = Some(normalized);
                                break;
                            }
                        }
                    }
                }
            }
        }
        
        let mod_date_keys = [
            "article:modified_time", "dateModified", "lastmod"
        ];
        
        for key in &mod_date_keys {
            if let Some(meta_node) = dom.query_selector(&format!("meta[property='{}'], meta[name='{}']", key, key))
                .and_then(|mut iter| iter.next()) {
                if let Some(node) = meta_node.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attrs = tag.attributes();
                        if let Some(content) = attrs.get("content").flatten() {
                            if let Some(normalized) = self.parse_date_string(&content.as_utf8_str()) {
                                document.modified_date = Some(normalized);
                                break;
                            }
                        }
                    }
                }
            }
        }

        // Check time elements
        if let Some(time_nodes) = dom.query_selector("time") {
            for node_handle in time_nodes {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attrs = tag.attributes();
                        if let Some(datetime) = attrs.get("datetime").flatten() {
                            if let Some(normalized) = self.parse_date_string(&datetime.as_utf8_str()) {
                                if document.published_date.is_none() {
                                    document.published_date = Some(normalized);
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn extract_canonical_url_if_different(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
        if let Some(canonical_node) = dom.query_selector("link[rel='canonical']").and_then(|mut iter| iter.next()) {
            if let Some(node) = canonical_node.get(parser) {
                if let Some(tag) = node.as_tag() {
                    if let Some(href) = tag.attributes().get("href").flatten() {
                        let canonical_url = href.as_utf8_str().to_string();
                        // Only store if different from base URL
                        if canonical_url != base_url {
                            document.canonical_url = Some(canonical_url);
                        }
                    }
                }
            }
        }
    }

    fn extract_main_content(&self, dom: &tl::VDom, parser: &Parser) -> String {
        // Priority selectors for main content (expanded list)
        let content_selectors = [
            "main", "article", ".content", ".post-content", ".entry-content",
            "#content", ".article-body", ".post-body", ".article-text",
            "[role='main']", ".main-content", ".page-content", ".content-wrapper",
            ".story-content", ".article-wrapper", ".text-content"
        ];
        
        // Try priority selectors first
        for selector in &content_selectors {
            if let Some(content_node) = dom.query_selector(selector).and_then(|mut iter| iter.next()) {
                if let Some(node) = content_node.get(parser) {
                    let content = self.extract_clean_text_from_node(node, parser);
                    if content.trim().len() > 100 {
                        return self.clean_body_text(&content);
                    }
                }
            }
        }
        
        // Enhanced fallback: extract text but filter out script/style/nav content
        if let Some(body_node) = dom.query_selector("body").and_then(|mut iter| iter.next()) {
            if let Some(node) = body_node.get(parser) {
                let raw_content = self.extract_clean_text_from_node(node, parser);
                return self.extract_readable_content(&raw_content);
            }
        }
        
        String::new()
    }
    
    /// Extract text from a node while filtering out script, style, and other noise elements
    fn extract_clean_text_from_node(&self, node: &Node, parser: &Parser) -> String {
        let mut clean_text = String::new();
        
        match node {
            Node::Tag(tag) => {
                let tag_name = tag.name().as_utf8_str().to_lowercase();
                
                // Skip script, style, noscript, and other noise elements
                if matches!(tag_name.as_str(), 
                    "script" | "style" | "noscript" | "nav" | "header" | "footer" | 
                    "aside" | "menu" | "menuitem" | "figure" | "figcaption" |
                    "button" | "input" | "select" | "textarea" | "form"
                ) {
                    return String::new();
                }
                
                // Skip elements with noise classes/IDs
                let attrs = tag.attributes();
                if let Some(class_val) = attrs.get("class").flatten() {
                    let class_str = class_val.as_utf8_str().to_lowercase();
                    if class_str.contains("nav") || class_str.contains("menu") || 
                       class_str.contains("sidebar") || class_str.contains("footer") ||
                       class_str.contains("header") || class_str.contains("ad") ||
                       class_str.contains("mw-parser-output") || class_str.contains("navbox") ||
                       class_str.contains("hlist") || class_str.contains("infobox") {
                        return String::new();
                    }
                }
                
                if let Some(id_val) = attrs.get("id").flatten() {
                    let id_str = id_val.as_utf8_str().to_lowercase();
                    if id_str.contains("nav") || id_str.contains("menu") || 
                       id_str.contains("sidebar") || id_str.contains("footer") ||
                       id_str.contains("header") || id_str.contains("ad") {
                        return String::new();
                    }
                }
                
                // Recursively extract text from child nodes
                for child in tag.children().top().iter() {
                    if let Some(child_node) = child.get(parser) {
                        clean_text.push_str(&self.extract_clean_text_from_node(child_node, parser));
                        clean_text.push(' ');
                    }
                }
            }
            Node::Raw(text) => {
                clean_text.push_str(&text.as_utf8_str());
            }
            _ => {}
        }
        
        clean_text
    }

    fn create_chunks_with_context(&self, content: &str, headings: &[Heading]) -> Vec<ChunkWithContext> {
        if content.is_empty() {
            return Vec::new();
        }

        // 🧹 Use FastCleaner for proper chunking with comprehensive cleaning
        let cleaner = FastCleaner::new();
        
        // First, clean the content thoroughly to remove HTML entities and noise
        let cleaned_content = cleaner.clean_text(content);
        
        // Use FastCleaner's optimized chunking method (with less restrictive size requirements)
        let raw_chunks = cleaner.create_chunks(&cleaned_content, 2500, 50);  // Reduced from 100 to 50
        
        let mut chunks_with_context = Vec::new();
        
        for (index, chunk_text) in raw_chunks.into_iter().enumerate() {
            // Additional filtering for web-specific noise that might slip through
            if self.is_chunk_meaningful(&chunk_text) && !self.contains_web_noise(&chunk_text) {
                let relevant_headings = self.find_relevant_headings_for_chunk(&chunk_text, headings);
                
                chunks_with_context.push(ChunkWithContext {
                    text_chunk: chunk_text,
                    relevant_headings,
                    chunk_index: index,
                });
            }
        }

        chunks_with_context
    }
    
    fn contains_web_noise(&self, text: &str) -> bool {
        let text_lower = text.to_lowercase();
        
        // Check for HTML-encoded entities that might slip through
        if text.contains("\\u003c") || text.contains("\\u003e") || 
           text.contains("\\u0026") || text.contains("&nbsp;") ||
           text.contains("&amp;") || text.contains("&lt;") || text.contains("&gt;") {
            return true;
        }
        
        // CRITICAL: Check for CSS patterns that indicate stylesheet content
        if text.contains(".mw-parser-output") || text.contains("navbox") ||
           text.contains("display:inline") || text.contains("margin:0") ||
           text.contains("padding:0") || text.contains("font-weight:bold") ||
           text.contains("background-color:") || text.contains("border:") ||
           text.contains("content:") || text.contains("::after") ||
           text.contains("::before") || text.contains(".hlist") ||
           text.contains("box-sizing:") || text.contains("line-height:") ||
           text.contains("text-align:") || text.contains("white-space:") ||
           text.contains("border-color:") || text.contains("border-left:") ||
           text.contains("border-top:") || text.contains("float:") ||
           text.contains("max-width:") || text.contains("@media") ||
           text.contains("counter-reset:") || text.contains("counter-increment:") {
            return true;
        }
        
        // Check for MediaWiki-specific patterns
        if text.contains("vtePart of") || text.contains("vteReligions") ||
           text.contains("Retrieved from") || text.contains("Hidden categories:") ||
           text.contains("Articles with") || text.contains("Pages with") ||
           text.contains("Webarchive template") || text.contains("Commons category") {
            return true;
        }
        
        // Check for JSON remnants
        if text.contains("\"type\":") || text.contains("\"href\":") || 
           text.contains("\"title\":") || text.contains("\"class\":") ||
           text.contains("\"id\":") || text.contains("\"style\":") {
            return true;
        }
        
        // Enhanced interface/navigation noise detection
        let interface_noise = [
            "diffhist", "talk contribs", "mobile edit", "visual edit", "android app",
            "ios app", "hidden tag", "wikiedu", "dashboard", "assignment wizard",
            "wikiloop", "battlefield", "user creation", "account", "antivandal",
            "rollback", "manual revert", "tag filter", "namespace", "template",
            "category", "portal", "module", "invert selection", "recent changes",
            "options", "hide", "show", "edit filter", "cleanup", "vandalism",
            "deletion", "backlogs", "village pump", "mailing lists", "signpost"
        ];
        
        // Count interface noise indicators
        let noise_count = interface_noise.iter()
            .map(|&noise| text_lower.matches(noise).count())
            .sum::<usize>();
        
        // If more than 20% of the text is interface noise, reject it
        let word_count = text.split_whitespace().count();
        if word_count > 0 && (noise_count as f32 / word_count as f32) > 0.2 {
            return true;
        }
        
        // Check for excessive CSS-like patterns (lots of colons and semicolons)
        let css_chars = text.chars().filter(|c| *c == ':' || *c == ';').count();
        if css_chars > 20 && text.len() > 500 {
            let css_density = css_chars as f32 / text.len() as f32;
            if css_density > 0.01 { // More than 1% CSS characters
                return true;
            }
        }
        
        // Check for excessive version numbers and technical IDs (like [1.0], [2.1], etc.)
        let version_pattern_count = text.matches(|c: char| c == '[' || c == ']').count();
        if version_pattern_count > 10 {
            return true;
        }
        
        // Check for excessive technical abbreviations and acronyms
        let uppercase_sequences = text.chars()
            .collect::<Vec<_>>()
            .windows(3)
            .filter(|window| window.iter().all(|c| c.is_uppercase() || !c.is_alphabetic()))
            .count();
        
        if uppercase_sequences > word_count / 4 {
            return true;
        }
        
        // Check for excessive navigation/link text
        let link_indicators = ["click here", "read more", "learn more", "view all", 
                              "home page", "contact us", "about us", "privacy policy"];
        if link_indicators.iter().any(|&indicator| text_lower.contains(indicator)) {
            // Only reject if it's mostly navigation content
            let total_words = text.split_whitespace().count();
            let nav_words = link_indicators.iter()
                .map(|&indicator| text_lower.matches(indicator).count() * indicator.split_whitespace().count())
                .sum::<usize>();
            
            if total_words > 0 && (nav_words as f32 / total_words as f32) > 0.3 {
                return true;
            }
        }
        
        false
    }
    
    fn is_chunk_meaningful(&self, chunk: &str) -> bool {
        let chunk = chunk.trim();
        
        // Must have minimum length (reduced from 30 to 20)
        if chunk.len() < 20 {
            return false;
        }
        
        // Check for reasonable sentence structure (reduced from 5 to 3 words)
        let words: Vec<&str> = chunk.split_whitespace().collect();
        if words.len() < 3 {
            return false;
        }
        
        // Must contain some alphabetic content (made more lenient)
        let alpha_chars = chunk.chars().filter(|c| c.is_alphabetic()).count();
        if alpha_chars < chunk.len() / 5 { // Reduced from 1/4 to 1/5
            return false;
        }
        
        // Check for too much JSON-like content (made more lenient)
        let json_chars = chunk.chars().filter(|c| "{}[]\",:;".contains(*c)).count();
        if json_chars > chunk.len() / 3 { // Increased from 1/4 to 1/3
            return false;
        }
        
        // Must contain some readable English words (made more lenient)
        let common_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "a", "an", "is", "are", "was", "were", "this", "that"];
        let word_count = common_words.iter().filter(|&word| {
            chunk.to_lowercase().contains(word)
        }).count();
        
        // Need at least 1 common word (was requiring any, now more explicit)
        word_count >= 1
    }

    fn find_relevant_headings_for_chunk(&self, chunk_text: &str, headings: &[Heading]) -> Vec<String> {
        // Simple relevance: headings that contain words from the chunk
        let chunk_words: std::collections::HashSet<String> = chunk_text
            .to_lowercase()
            .split_whitespace()
            .filter(|w| w.len() > 3)
            .take(20) // Only check first 20 words for performance
            .map(|w| w.to_string())
            .collect();

        headings
            .iter()
            .filter_map(|heading| {
                let heading_words: std::collections::HashSet<String> = heading.text
                    .to_lowercase()
                    .split_whitespace()
                    .map(|w| w.to_string())
                    .collect();

                // If heading shares words with chunk, it's relevant
                let intersection: Vec<_> = chunk_words.intersection(&heading_words).collect();
                if intersection.len() > 0 {
                    Some(heading.text.clone())
                } else {
                    None
                }
            })
            .take(3) // Max 3 relevant headings per chunk
            .collect()
    }

    fn extract_essential_from_json_ld(&self, json_value: &serde_json::Value, structured_meta: &mut StructuredMeta) {
        if let Some(obj) = json_value.as_object() {
            // Extract article type
            if let Some(type_val) = obj.get("@type") {
                if let Some(type_str) = type_val.as_str() {
                    structured_meta.article_type = Some(type_str.to_string());
                }
            }

            // Extract featured image
            if let Some(image_val) = obj.get("image") {
                let image_url = match image_val {
                    serde_json::Value::String(s) => Some(s.clone()),
                    serde_json::Value::Object(img_obj) => {
                        img_obj.get("url").and_then(|u| u.as_str()).map(|s| s.to_string())
                    }
                    _ => None
                };
                if let Some(url) = image_url {
                    structured_meta.featured_image = Some(url);
                }
            }

            // Extract publisher name
            if let Some(publisher_val) = obj.get("publisher") {
                let publisher_name = match publisher_val {
                    serde_json::Value::String(s) => Some(s.clone()),
                    serde_json::Value::Object(pub_obj) => {
                        pub_obj.get("name").and_then(|n| n.as_str()).map(|s| s.to_string())
                    }
                    _ => None
                };
                if let Some(name) = publisher_name {
                    structured_meta.publisher_name = Some(name);
                }
            }

            // Extract dates
            if let Some(date_pub) = obj.get("datePublished").and_then(|d| d.as_str()) {
                structured_meta.date_published = Some(date_pub.to_string());
            }
            if let Some(date_mod) = obj.get("dateModified").and_then(|d| d.as_str()) {
                structured_meta.date_modified = Some(date_mod.to_string());
            }
        }
    }

    fn resolve_url(&self, url: &str, base_url: &str) -> String {
        if url.starts_with("http") {
            url.to_string()
        } else if url.starts_with("//") {
            format!("https:{}", url)
        } else if url.starts_with("/") {
            // Extract domain from base_url
            if let Ok(parsed) = url::Url::parse(base_url) {
                format!("{}://{}{}", parsed.scheme(), parsed.host_str().unwrap_or(""), url)
            } else {
                url.to_string()
            }
        } else {
            format!("{}/{}", base_url.trim_end_matches('/'), url)
        }
    }

    fn clean_body_text(&self, text: &str) -> String {
        // Remove extra whitespace and clean up
        let cleaned = text
            .lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty() && line.len() > 10)
            .collect::<Vec<_>>()
            .join(" ");
        
        // Remove excessive whitespace
        let regex = regex::Regex::new(r"\s+").unwrap();
        regex.replace_all(&cleaned, " ").trim().to_string()
    }

    fn extract_readable_content(&self, raw_content: &str) -> String {
        // Filter out common noise patterns found in modern web pages
        let lines: Vec<&str> = raw_content
            .lines()
            .map(|line| line.trim())
            .filter(|line| {
                // Skip empty lines
                if line.is_empty() || line.len() < 10 {
                    return false;
                }
                
                // Skip lines that look like JSON data
                if line.starts_with('{') || line.starts_with('[') || 
                   line.contains("\"props\"") || line.contains("\"pageProps\"") ||
                   line.contains("\"@type\"") || line.contains("\"contentType\"") ||
                   line.contains("\"href\"") || line.contains("\"metadata\"") {
                    return false;
                }
                
                // Skip navigation and UI elements
                if line.contains("Sign in") || line.contains("Register") ||
                   line.contains("Menu") || line.contains("Search") ||
                   line.contains("Subscribe") || line.contains("Follow") ||
                   line.contains("Share") || line.contains("Like") ||
                   line.contains("Tweet") || line.contains("Facebook") {
                    return false;
                }
                
                // Skip lines with excessive special characters (likely JSON/code)
                let special_char_count = line.chars().filter(|c| "{}[]\",:;".contains(*c)).count();
                if special_char_count > line.len() / 4 {
                    return false;
                }
                
                // Skip URLs and technical strings
                if line.starts_with("http") || line.starts_with("www.") ||
                   line.contains("javascript:") || line.contains("mailto:") ||
                   line.contains("tel:") {
                    return false;
                }
                
                // Skip lines that are mostly numbers or IDs
                let non_alphanumeric: usize = line.chars().filter(|c| !c.is_alphanumeric() && *c != ' ').count();
                if non_alphanumeric > line.len() / 3 {
                    return false;
                }
                
                true
            })
            .collect();
            
        let filtered_content = lines.join(" ");
        
        // Final cleanup
        self.clean_body_text(&filtered_content)
    }

    fn annotate_technical_content(&self, content: &str) -> String {
        // Simple annotation for technical content
        content.to_string()
    }

    fn calculate_essential_metrics(&self, document: &mut ProcessedDocument) {
        let words: Vec<&str> = document.main_content
            .split_whitespace()
            .filter(|w| w.len() > 2)
            .collect();
        
        document.word_count = words.len();
        
        // Calculate semantic info with essential fields only
        document.semantic_info = SemanticInfo {
            word_count: document.word_count,
            sentence_count: document.main_content.matches('.').count(),
            paragraph_count: document.main_content.matches('\n').count().max(1),
            reading_time_minutes: (document.word_count as f32 / 200.0).max(1.0),
            content_quality_score: self.calculate_quality_score(&document.main_content, &document.headings),
            is_technical_content: self.calculate_technical_score(&document.main_content) > 0.3,
            headings_count: document.headings.len(),
            images_count: if document.primary_image.is_some() { 1 } else { 0 },
            links_count: 0, // We don't extract links in optimized version
            technical_score: self.calculate_technical_score(&document.main_content),
            avg_sentence_length: if document.semantic_info.sentence_count > 0 {
                document.word_count as f32 / document.semantic_info.sentence_count as f32
            } else { 0.0 },
            content_density: document.word_count as f32 / document.main_content.len().max(1) as f32,
        };
        
        document.content_quality_score = document.semantic_info.content_quality_score;
    }

    fn calculate_quality_score(&self, content: &str, headings: &[Heading]) -> f32 {
        let mut score = 0.0;
        
        // Length scoring
        let word_count = content.split_whitespace().count() as f32;
        if word_count > 100.0 {
            score += (word_count / 1000.0).min(3.0);
        }
        
        // Structure scoring
        if !headings.is_empty() {
            score += 1.0;
        }
        
        if headings.len() > 2 {
            score += 0.5;
        }
        
        score.min(5.0)
    }

    fn calculate_technical_score(&self, content: &str) -> f32 {
        let technical_count = self.tech_pattern.find_iter(content).count();
        (technical_count as f32 / content.len().max(1) as f32) * 1000.0
    }

    fn is_technical_content(&self, document: &ProcessedDocument) -> bool {
        document.semantic_info.technical_score > 0.3 || 
        document.semantic_info.is_technical_content
    }

    fn extract_keywords_from_content(&self, content: &str, max_keywords: usize) -> Vec<String> {
        let content_lower = content.to_lowercase();
        let words: Vec<&str> = content_lower
            .split_whitespace()
            .filter(|w| w.len() > 3 && !w.chars().all(|c| !c.is_alphabetic()))
            .collect();

        let mut word_counts = std::collections::HashMap::new();
        for word in words {
            *word_counts.entry(word.to_string()).or_insert(0) += 1;
        }

        let mut sorted_words: Vec<_> = word_counts.into_iter().collect();
        sorted_words.sort_by(|a, b| b.1.cmp(&a.1));

        sorted_words
            .into_iter()
            .take(max_keywords)
            .map(|(word, _)| word)
            .collect()
    }

    fn parse_date_string(&self, date_str: &str) -> Option<String> {
        // Simple date parsing - use chrono for proper parsing
        if let Ok(dt) = DateTime::parse_from_rfc3339(date_str) {
            return Some(dt.to_utc().to_rfc3339());
        }
        
        // Try other common formats
        for pattern in &self.date_patterns {
            if pattern.is_match(date_str) {
                // For now, return the original string if it matches a pattern
                return Some(date_str.to_string());
            }
        }
        
        None
    }
}
