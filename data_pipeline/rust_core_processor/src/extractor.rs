use std::collections::HashMap;
use tl::{Parser, HTMLTag, Node};
use regex::Regex;
use chrono::{DateTime, NaiveDateTime, Utc, TimeZone, NaiveDate};
use crate::types::*;

pub struct FastExtractor {
    // Precompiled regex patterns for performance
    api_pattern: Regex,
    function_pattern: Regex,
    tech_pattern: Regex,
    date_patterns: Vec<Regex>,
    url_pattern: Regex,
    email_pattern: Regex,
}

impl FastExtractor {
    pub fn new() -> Self {
        // Technical content patterns
        let tech_keywords = [
            "api", "function", "method", "parameter", "interface", "implementation",
            "algorithm", "array", "binary", "cache", "compiler", "concurrency", "container",
            "database", "debug", "encryption", "framework", "frontend", "backend",
            "hash", "inheritance", "instance", "iteration", "json", "kernel", "middleware",
            "microservice", "module", "namespace", "network", "object", "operator",
            "query", "queue", "recursive", "repository", "runtime", "scalability", "schema", "script",
            "serialization", "sdk", "service", "session", "stack", "stream", "syntax", "thread",
            "token", "url", "validation", "virtual", "volatile", "websocket", "xml", "yaml",
            "buffer", "bytecode", "cli", "cluster", "docker", "gateway", "host", "index", "latency",
            "mutex", "node", "router", "ssl", "tcp", "udp", "ux", "vm",
            "ai", "machine learning", "deep learning", "neural", "neuron", "tensor", "regression",
            "classification", "clustering", "random forest", "gradient boosting", "svm", "knn",
            "cnn", "rnn", "transformer", "attention", "nlp", "computer vision", "feature", "label",
            "training", "inference", "overfitting", "underfitting", "cross validation",
            "hyperparameter", "optimizer", "backpropagation", "epoch", "dataset",
            "pipeline", "preprocessing", "augmentation", "embedding", "vector", "pytorch", "tensorflow",
            "keras", "sklearn", "xgboost", "lightgbm", "blockchain", "smart contract", "web3",
            "metaverse", "iot", "edge computing", "serverless", "kubernetes", "helm", "istio",
            "service mesh", "graphql", "observability", "prometheus", "grafana", "ci/cd", "devops",
            "gitops", "terraform", "ansible", "chaos engineering", "defi", "nft", "quantum computing",
            "5g", "augmented reality", "virtual reality", "digital twin", "microfrontend", "edge ai"
        ];
        
        let tech_pattern_str = tech_keywords.join("|");
        
        // Date patterns for extraction
        let date_patterns = vec![
            Regex::new(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}").unwrap(), // ISO format
            Regex::new(r"\d{4}-\d{2}-\d{2}").unwrap(), // Simple date
            Regex::new(r"\d{2}/\d{2}/\d{4}").unwrap(), // MM/DD/YYYY
            Regex::new(r"\d{2}-\d{2}-\d{4}").unwrap(), // MM-DD-YYYY
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
        document.canonical_url = base_url.to_string();
        
        // Single-pass extraction of all metadata
        self.extract_all_metadata(&dom, parser, &mut document, base_url);
        
        // Extract and clean main content
        let raw_content = self.extract_main_content(&dom, parser);
        document.main_content = self.annotate_technical_content(&raw_content);
        
        // Generate keywords from content if no meta keywords found
        if document.keywords.is_empty() {
            document.keywords = self.extract_keywords_from_content(&document.main_content, 10);
        }
        
        // Calculate comprehensive metrics
        self.calculate_comprehensive_metrics(&mut document);
        
        // Detect technical content
        document.is_technical_content = self.is_technical_content(&document);
        
        document
    }

    
    fn extract_all_metadata(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
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
        
        // Extract meta tags and structured data
        self.extract_meta_tags(dom, parser, document);
        self.extract_structured_data(dom, parser, document);
        
        // Extract headings and build table of contents
        self.extract_headings(dom, parser, document);
        
        // Extract images with full metadata
        self.extract_images(dom, parser, document, base_url);
        
        // Extract links
        self.extract_links(dom, parser, document, base_url);
        
        // Extract author information
        self.extract_author_info(dom, parser, document);
        
        // Extract publication dates
        self.extract_publication_dates(dom, parser, document);
        
        // Extract icons and favicon
        self.extract_icons(dom, parser, document, base_url);
    }
    
    fn extract_meta_tags(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        if let Some(meta_nodes) = dom.query_selector("meta") {
            for node_handle in meta_nodes {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(HTMLTag { .. }) = node.as_tag() {
                        let attributes = node.as_tag().unwrap().attributes();
                        let mut key = String::new();
                        let mut content = String::new();
                        
                        // Get content first
                        if let Some(content_attr) = attributes.get("content").flatten() {
                            content = content_attr.as_utf8_str().trim().to_string();
                        }
                        
                        // Determine the key - Enhanced patterns like Python
                        if let Some(name) = attributes.get("name").flatten() {
                            key = format!("name:{}", name.as_utf8_str());
                        } else if let Some(property) = attributes.get("property").flatten() {
                            key = format!("property:{}", property.as_utf8_str());
                        } else if let Some(itemprop) = attributes.get("itemprop").flatten() {
                            key = format!("itemprop:{}", itemprop.as_utf8_str());
                        } else if let Some(http_equiv) = attributes.get("http-equiv").flatten() {
                            key = format!("http-equiv:{}", http_equiv.as_utf8_str());
                        }
                        
                        if !key.is_empty() && !content.is_empty() {
                            // Store in appropriate collections
                            document.meta_tags.insert(key.clone(), content.clone());
                            
                            // Parse specific meta types
                            if key.starts_with("property:og:") {
                                let og_key = key.replace("property:og:", "");
                                document.open_graph.insert(og_key, content.clone());
                            } else if key.starts_with("name:twitter:") {
                                let twitter_key = key.replace("name:twitter:", "");
                                document.twitter_cards.insert(twitter_key, content.clone());
                            }
                            
                            // Extract core metadata - Enhanced patterns like Python
                            match key.as_str() {
                                // Description from multiple sources
                                "property:og:description" | "name:description" | "name:twitter:description" | 
                                "property:description" | "name:DC.Description" | "name:dc.description" | 
                                "itemprop:description" => {
                                    if document.description.is_empty() && content.len() > 10 {
                                        document.description = content.clone();
                                    }
                                }
                                
                                // Categories and tags - NEW ENHANCED EXTRACTION
                                "property:article:section" | "name:category" | "name:categories" |
                                "property:og:type" | "name:subject" | "name:news_keywords" |
                                "property:article:tag" | "name:tags" | "itemprop:keywords" |
                                "name:DC.Subject" | "name:dc.subject" => {
                                    let categories: Vec<String> = if content.contains(',') {
                                        content.split(',').collect::<Vec<&str>>()
                                    } else if content.contains(';') {
                                        content.split(';').collect::<Vec<&str>>()
                                    } else {
                                        vec![content.as_str()]
                                    }.iter()
                                     .map(|c| c.trim().to_lowercase())
                                     .filter(|c| !c.is_empty() && c.len() >= 3 && c.len() <= 30)
                                     .collect();
                                    
                                    document.content_categories.extend(categories);
                                    // Remove duplicates and limit
                                    document.content_categories.sort();
                                    document.content_categories.dedup();
                                    document.content_categories.truncate(10);
                                }
                                
                                // Keywords from multiple sources - Enhanced patterns like Python
                                "name:keywords" | "property:keywords" => {
                                    let keywords: Vec<String> = if content.contains(',') {
                                        content.split(',').collect::<Vec<&str>>()
                                    } else if content.contains(';') {
                                        content.split(';').collect::<Vec<&str>>()
                                    } else {
                                        content.split_whitespace().collect::<Vec<&str>>()
                                    }.iter()
                                     .map(|k| k.trim().to_lowercase())
                                     .filter(|k| !k.is_empty() && k.len() >= 3 && k.len() <= 30)
                                     .collect();
                                    
                                    document.keywords.extend(keywords);
                                    // Remove duplicates and limit to 15
                                    document.keywords.sort();
                                    document.keywords.dedup();
                                    document.keywords.truncate(15);
                                }
                                
                                // Publication dates - Enhanced extraction with better parsing
                                "property:article:published_time" | "name:publication_date" | 
                                "property:published_time" | "name:date" | "itemprop:datePublished" |
                                "name:pubdate" | "name:DC.Date" | "name:dc.date" => {
                                    if document.published_date.is_none() {
                                        // Clean and parse the date
                                        let cleaned_date = self.clean_date_string(&content);
                                        document.published_date = Some(cleaned_date);
                                    }
                                }
                                
                                // Modified dates - Enhanced extraction with better parsing
                                "property:article:modified_time" | "name:modified_date" | 
                                "property:modified_time" | "itemprop:dateModified" |
                                "name:last-modified" | "name:DC.Date.Modified" => {
                                    if document.modified_date.is_none() {
                                        // Clean and parse the date
                                        let cleaned_date = self.clean_date_string(&content);
                                        document.modified_date = Some(cleaned_date);
                                    }
                                }
                                
                                _ => {}
                            }
                        }
                    }
                }
            }
        }
        
        // Extract canonical URL
        if let Some(canonical_node) = dom.query_selector("link[rel='canonical']").and_then(|mut iter| iter.next()) {
            if let Some(node) = canonical_node.get(parser) {
                if let Some(tag) = node.as_tag() {
                    if let Some(href) = tag.attributes().get("href").flatten() {
                        document.canonical_url = href.as_utf8_str().to_string();
                    }
                }
            }
        }
    }
    
    fn extract_structured_data(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        // Extract JSON-LD with enhanced error handling
        if let Some(script_nodes) = dom.query_selector("script[type*='ld+json'], script[type*='application/ld+json']") {
            for node_handle in script_nodes {
                if let Some(node) = node_handle.get(parser) {
                    let script_content_full = node.inner_text(parser);
                    let script_content = script_content_full.trim();
                    if !script_content.is_empty() {
                        // Clean the JSON content
                        let cleaned_content = script_content
                            .replace("\\\"", "\"")
                            .replace("\n", "")
                            .replace("\t", "");
                        
                        match serde_json::from_str::<serde_json::Value>(&cleaned_content) {
                            Ok(json_value) => {
                                document.structured_data.json_ld.push(json_value.clone());
                                
                                // Extract additional metadata from JSON-LD
                                self.extract_from_json_ld(&json_value, document);
                            }
                            Err(_) => {
                                // Try to extract as raw JSON string for storage
                                if cleaned_content.len() < 5000 { // Reasonable size limit
                                    document.structured_data.json_ld.push(serde_json::Value::String(cleaned_content));
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // Extract microdata with enhanced property extraction
        if let Some(microdata_nodes) = dom.query_selector("[itemscope]") {
            for node_handle in microdata_nodes.take(20) { // Limit for performance
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attributes = tag.attributes();
                        let mut item_data = HashMap::new();
                        
                        if let Some(itemtype) = attributes.get("itemtype").flatten() {
                            let type_url = itemtype.as_utf8_str();
                            if let Some(type_name) = type_url.split('/').last() {
                                item_data.insert("@type".to_string(), type_name.to_string());
                            }
                        }
                        
                        // Extract properties within this scope
                        if let Some(prop_nodes) = dom.query_selector("[itemprop]") {
                            for prop_handle in prop_nodes.take(50) {
                                if let Some(prop_node) = prop_handle.get(parser) {
                                    if let Some(prop_tag) = prop_node.as_tag() {
                                        let prop_attrs = prop_tag.attributes();
                                        let name = prop_tag.name();
                                        if let Some(itemprop) = prop_attrs.get("itemprop").flatten() {
                                            let prop_name = itemprop.as_utf8_str().to_string();
                                            let prop_value = match name.as_bytes() {
                                                b"meta" => prop_attrs.get("content").flatten().map(|v| v.as_utf8_str().to_string()),
                                                b"time" => prop_attrs.get("datetime").flatten().map(|v| v.as_utf8_str().to_string())
                                                    .or_else(|| Some(prop_node.inner_text(parser).trim().to_string())),
                                                b"img" => prop_attrs.get("src").flatten().map(|v| v.as_utf8_str().to_string()),
                                                b"a" => prop_attrs.get("href").flatten().map(|v| v.as_utf8_str().to_string()),
                                                _ => Some(prop_node.inner_text(parser).trim().to_string()),
                                            };
                                            
                                            if let Some(value) = prop_value {
                                                if !value.is_empty() && value.len() < 500 {
                                                    item_data.insert(prop_name, value);
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        if !item_data.is_empty() {
                            document.structured_data.microdata.push(item_data);
                        }
                    }
                }
            }
        }
        
        // Extract RDFa with enhanced property extraction
        if let Some(rdfa_nodes) = dom.query_selector("[property], [typeof]") {
            for node_handle in rdfa_nodes.take(30) {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attributes = tag.attributes();
                        let mut rdfa_data = HashMap::new();
                        
                        if let Some(type_of) = attributes.get("typeof").flatten() {
                            rdfa_data.insert("@type".to_string(), type_of.as_utf8_str().to_string());
                        }
                        
                        if let Some(property) = attributes.get("property").flatten() {
                            let prop_name = property.as_utf8_str().to_string();
                            let content = if let Some(content_attr) = attributes.get("content").flatten() {
                                content_attr.as_utf8_str().to_string()
                            } else {
                                node.inner_text(parser).trim().to_string()
                            };
                            
                            if !content.is_empty() && content.len() < 500 {
                                rdfa_data.insert(prop_name, content);
                            }
                        }
                        
                        if !rdfa_data.is_empty() {
                            document.structured_data.rdfa.push(rdfa_data);
                        }
                    }
                }
            }
        }
    }
    
    fn extract_headings(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        for level in 1..=6 {
            let selector = format!("h{}", level);
            if let Some(heading_nodes) = dom.query_selector(&selector) {
                for node_handle in heading_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        let text = node.inner_text(parser).trim().to_string();
                        if !text.is_empty() && text.len() > 1 {
                            let mut heading = Heading {
                                level: level as u8,
                                text: text.clone(),
                                id: String::new(),
                                class: String::new(),
                            };
                            
                            if let Some(tag) = node.as_tag() {
                                let attributes = tag.attributes();
                                
                                // Enhanced ID extraction
                                if let Some(id) = attributes.get("id").flatten() {
                                    heading.id = id.as_utf8_str().to_string();
                                } else {
                                    // Generate ID from text if none exists
                                    heading.id = self.generate_anchor_id(&text);
                                }
                                
                                if let Some(class) = attributes.get("class").flatten() {
                                    heading.class = class.as_utf8_str().to_string();
                                }
                            }
                            
                            document.headings.push(heading.clone());
                            
                            // Create table of contents entry with enhanced anchor
                            let mut toc_entry = heading.clone();
                            if toc_entry.id.is_empty() {
                                toc_entry.id = self.generate_anchor_id(&text);
                            }
                            document.table_of_contents.push(toc_entry);
                        }
                    }
                }
            }
        }
        
        // Also extract navigation elements and lists that might be TOC
        if let Some(nav_nodes) = dom.query_selector("nav, .toc, .table-of-contents, [role='navigation']") {
            for node_handle in nav_nodes.take(5) {
                if let Some(_node) = node_handle.get(parser) {
                    if let Some(link_nodes) = dom.query_selector("a[href^='#']") {
                        for link_handle in link_nodes.take(20) {
                            if let Some(link_node) = link_handle.get(parser) {
                                if let Some(link_tag) = link_node.as_tag() {
                                    let link_text_full = link_node.inner_text(parser);
                                    let link_text = link_text_full.trim();
                                    if let Some(href) = link_tag.attributes().get("href").flatten() {
                                        let href_full = href.as_utf8_str();
                                        let anchor = href_full.trim_start_matches('#');
                                        if !link_text.is_empty() && !anchor.is_empty() {
                                            let toc_heading = Heading {
                                                level: 2, // Default level for nav links
                                                text: link_text.to_string(),
                                                id: anchor.to_string(),
                                                class: "nav-link".to_string(),
                                            };
                                            document.table_of_contents.push(toc_heading);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    fn extract_images(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
        if let Some(img_nodes) = dom.query_selector("img") {
            for node_handle in img_nodes.take(25) { // Increased limit
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attributes = tag.attributes();
                        if let Some(src) = attributes.get("src").flatten() {
                            let src_str = src.as_utf8_str();
                            
                            // Skip tiny images, tracking pixels, and placeholders
                            if src_str.contains("1x1") || src_str.contains("pixel") || src_str.contains("tracker") {
                                continue;
                            }
                            
                            let full_src = if src_str.starts_with("http") {
                                src_str.to_string()
                            } else if src_str.starts_with("//") {
                                format!("https:{}", src_str)
                            } else {
                                format!("{}/{}", base_url.trim_end_matches('/'), src_str.trim_start_matches('/'))
                            };
                            
                            // Enhanced alt text extraction
                            let alt = attributes.get("alt").flatten()
                                .map(|v| v.as_utf8_str().trim().to_string())
                                .filter(|s| !s.is_empty())
                                .or_else(|| {
                                    // Fallback: try to extract from aria-label
                                    attributes.get("aria-label").flatten()
                                        .map(|v| v.as_utf8_str().trim().to_string())
                                        .filter(|s| !s.is_empty())
                                })
                                .or_else(|| {
                                    // Fallback: try to extract from data-alt
                                    attributes.get("data-alt").flatten()
                                        .map(|v| v.as_utf8_str().trim().to_string())
                                        .filter(|s| !s.is_empty())
                                })
                                .unwrap_or_default();
                            
                            // Enhanced title extraction
                            let title = attributes.get("title").flatten()
                                .map(|v| v.as_utf8_str().trim().to_string())
                                .filter(|s| !s.is_empty())
                                .or_else(|| {
                                    // Fallback: try to extract from data-title
                                    attributes.get("data-title").flatten()
                                        .map(|v| v.as_utf8_str().trim().to_string())
                                        .filter(|s| !s.is_empty())
                                })
                                .or_else(|| {
                                    // Fallback: use alt if no title
                                    if !alt.is_empty() { Some(alt.clone()) } else { None }
                                })
                                .unwrap_or_default();
                            
                            let image = ImageInfo {
                                src: full_src,
                                alt,
                                title,
                                width: attributes.get("width").flatten().map_or(String::new(), |v| v.as_utf8_str().to_string()),
                                height: attributes.get("height").flatten().map_or(String::new(), |v| v.as_utf8_str().to_string()),
                            };
                            
                            document.images.push(image);
                        }
                    }
                }
            }
        }
        
        // Also extract background images from CSS styles
        if let Some(styled_nodes) = dom.query_selector("[style*='background-image']") {
            for node_handle in styled_nodes.take(10) {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        if let Some(style) = tag.attributes().get("style").flatten() {
                            let style_str = style.as_utf8_str();
                            if let Some(url_start) = style_str.find("url(") {
                                if let Some(url_end) = style_str[url_start..].find(")") {
                                    let url_content = &style_str[url_start + 4..url_start + url_end];
                                    let cleaned_url = url_content.trim_matches('"').trim_matches('\'');
                                    
                                    if !cleaned_url.is_empty() && !cleaned_url.contains("data:") {
                                        let full_src = if cleaned_url.starts_with("http") {
                                            cleaned_url.to_string()
                                        } else {
                                            format!("{}/{}", base_url.trim_end_matches('/'), cleaned_url.trim_start_matches('/'))
                                        };
                                        
                                        let image = ImageInfo {
                                            src: full_src,
                                            alt: "Background image".to_string(),
                                            title: "CSS background image".to_string(),
                                            width: String::new(),
                                            height: String::new(),
                                        };
                                        
                                        document.images.push(image);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    fn extract_links(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
        if let Some(link_nodes) = dom.query_selector("a[href]") {
            for node_handle in link_nodes.take(50) { // Limit for performance
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attributes = tag.attributes();
                        if let Some(href) = attributes.get("href").flatten() {
                            let href_str = href.as_utf8_str();
                            let text = node.inner_text(parser).trim().to_string();
                            
                            if !href_str.is_empty() && !text.is_empty() {
                                let rel = attributes.get("rel").flatten().map_or(vec![], |v| {
                                    v.as_utf8_str().split_whitespace().map(|s| s.to_string()).collect()
                                });
                                
                                // Check for canonical URL
                                if rel.contains(&"canonical".to_string()) {
                                    document.canonical_url = if href_str.starts_with("http") {
                                        href_str.to_string()
                                    } else {
                                        format!("{}/{}", base_url.trim_end_matches('/'), href_str.trim_start_matches('/'))
                                    };
                                }
                                
                                let link = LinkInfo {
                                    href: href_str.to_string(),
                                    text,
                                    rel,
                                    title: attributes.get("title").flatten().map_or(String::new(), |v| v.as_utf8_str().to_string()),
                                    is_external: href_str.starts_with("http") && !href_str.contains(base_url),
                                };
                                
                                document.links.push(link);
                            }
                        }
                    }
                }
            }
        }
        
        // Also check link tags for canonical
        if let Some(link_tags) = dom.query_selector("link[rel='canonical']") {
            for node_handle in link_tags {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attributes = tag.attributes();
                        if let Some(href) = attributes.get("href").flatten() {
                            let href_str = href.as_utf8_str();
                            document.canonical_url = if href_str.starts_with("http") {
                                href_str.to_string()
                            } else {
                                format!("{}/{}", base_url.trim_end_matches('/'), href_str.trim_start_matches('/'))
                            };
                            break;
                        }
                    }
                }
            }
        }
    }
    
    fn extract_author_info(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        // Enhanced author extraction to match Python patterns
        
        // Method 1: Meta tags (enhanced with more patterns)
        let meta_patterns = [
            "name:author",
            "property:article:author", 
            "name:twitter:creator",
            "property:og:article:author",
            "name:dc.creator",
            "name:DC.Creator",
            "name:article:author_name",
            "name:sailthru.author",
            "property:book:author",
            "name:byl",
            "name:author-name"
        ];
        
        for pattern in &meta_patterns {
            if let Some(content) = document.meta_tags.get(*pattern) {
                if !content.is_empty() && document.author_info.name.is_empty() {
                    document.author_info.name = content.clone();
                    document.author_info.url = format!("meta:{}", pattern);
                    break;
                }
            }
        }
        
        // Method 2: Enhanced HTML patterns - matches Python patterns
        let author_selectors = [
            "[rel='author']",
            "[itemprop='author']",
            ".author", ".byline", ".writer", ".creator", ".contributor",
            ".author-name", ".post-author", ".entry-author", ".article-author", ".byline-author",
            "[data-testid='author']", ".writer-name",
            "[data-author]",
            "#author", "#byline"
        ];
        
        for selector in &author_selectors {
            if let Some(author_nodes) = dom.query_selector(selector) {
                for node_handle in author_nodes.take(3) {
                    if let Some(node) = node_handle.get(parser) {
                        let text = node.inner_text(parser).trim().to_string();
                        if !text.is_empty() && text.len() <= 200 && document.author_info.name.is_empty() {
                            document.author_info.name = text;
                            
                            // Try to extract author URL if it's a link
                            if let Some(tag) = node.as_tag() {
                                if let Some(href) = tag.attributes().get("href").flatten() {
                                    let href_str = href.as_utf8_str();
                                    if href_str.starts_with("http") {
                                        document.author_info.url = href_str.to_string();
                                    }
                                }
                            }
                            break;
                        }
                    }
                }
                if !document.author_info.name.is_empty() {
                    break;
                }
            }
        }
        
        // Method 3: Extract from structured data (JSON-LD)
        for json_obj in &document.structured_data.json_ld {
            if let Some(author) = json_obj.get("author") {
                if let Some(author_obj) = author.as_object() {
                    if let Some(name) = author_obj.get("name").and_then(|n| n.as_str()) {
                        if document.author_info.name.is_empty() {
                            document.author_info.name = name.to_string();
                        }
                    }
                    if let Some(url) = author_obj.get("url").and_then(|u| u.as_str()) {
                        if document.author_info.url.is_empty() {
                            document.author_info.url = url.to_string();
                        }
                    }
                } else if let Some(author_str) = author.as_str() {
                    if document.author_info.name.is_empty() {
                        document.author_info.name = author_str.to_string();
                    }
                }
                if !document.author_info.name.is_empty() {
                    break;
                }
            }
        }
        
        // Author extraction complete - no logging needed
    }
    
    fn extract_publication_dates(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument) {
        // Check meta tags first (enhanced patterns)
        let pub_date_keys = [
            "property:article:published_time",
            "name:article:published_time",
            "name:publication_date",
            "name:date",
            "name:pubdate",
            "name:DC.Date",
            "property:og:article:published_time",
            "name:sailthru.date",
            "name:publish-date",
            "name:publishdate",
            "name:article.published",
            "name:datePublished",
            "property:article:published",
            "name:twitter:label1"
        ];
        
        for key in &pub_date_keys {
            if let Some(date_str) = document.meta_tags.get(*key) {
                if !date_str.is_empty() {
                    if let Some(parsed_date) = self.parse_date_string(date_str) {
                        document.published_date = Some(parsed_date);
                        break;
                    }
                }
            }
        }
        
        let mod_date_keys = [
            "property:article:modified_time",
            "name:article:modified_time", 
            "name:last-modified",
            "name:DC.Date.Modified"
        ];
        
        for key in &mod_date_keys {
            if let Some(date_str) = document.meta_tags.get(*key) {
                if !date_str.is_empty() {
                    if let Some(parsed_date) = self.parse_date_string(date_str) {
                        document.modified_date = Some(parsed_date);
                        break;
                    }
                }
            }
        }
        
        // Check time elements
        if let Some(time_nodes) = dom.query_selector("time") {
            for node_handle in time_nodes.take(5) {
                if let Some(node) = node_handle.get(parser) {
                    if let Some(tag) = node.as_tag() {
                        let attributes = tag.attributes();
                        let datetime = attributes.get("datetime").flatten()
                            .map(|v| v.as_utf8_str().to_string())
                            .or_else(|| {
                                let inner_text = node.inner_text(parser);
                                let text = inner_text.trim();
                                if text.is_empty() { None } else { Some(text.to_string()) }
                            });
                        
                        if let Some(date_str) = datetime {
                            if !date_str.is_empty() {
                                if let Some(parsed_date) = self.parse_date_string(&date_str) {
                                    if document.published_date.is_none() {
                                        document.published_date = Some(parsed_date);
                                    } else if document.modified_date.is_none() {
                                        document.modified_date = Some(parsed_date);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    fn extract_icons(&self, dom: &tl::VDom, parser: &Parser, document: &mut ProcessedDocument, base_url: &str) {
        let icon_selectors = [
            ("icon", "link[rel='icon']"),
            ("shortcut icon", "link[rel='shortcut icon']"), 
            ("apple-touch-icon", "link[rel='apple-touch-icon']"),
            ("apple-touch-icon-precomposed", "link[rel='apple-touch-icon-precomposed']"),
            ("mask-icon", "link[rel='mask-icon']"),
            ("fluid-icon", "link[rel='fluid-icon']")
        ];
        
        for (rel_name, selector) in &icon_selectors {
            if let Some(icon_nodes) = dom.query_selector(selector) {
                for node_handle in icon_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        if let Some(tag) = node.as_tag() {
                            let attributes = tag.attributes();
                            if let Some(href) = attributes.get("href").flatten() {
                                let href_str = href.as_utf8_str();
                                let full_url = if href_str.starts_with("http") {
                                    href_str.to_string()
                                } else if href_str.starts_with("//") {
                                    format!("https:{}", href_str)
                                } else {
                                    format!("{}/{}", base_url.trim_end_matches('/'), href_str.trim_start_matches('/'))
                                };
                                
                                document.icons.insert(rel_name.to_string(), full_url);
                            }
                        }
                    }
                }
            }
        }
        
        // Also check for standard favicon.ico
        if document.icons.is_empty() {
            let favicon_url = format!("{}/favicon.ico", base_url.trim_end_matches('/'));
            document.icons.insert("icon".to_string(), favicon_url);
        }
    }
    
    fn extract_main_content(&self, dom: &tl::VDom, parser: &Parser) -> String {
        // Priority selectors for main content
        let content_selectors = [
            "main",
            "article", 
            "[role='main']",
            ".content",
            ".post-content",
            ".entry-content",
            ".article-content",
            "#content",
            "#main",
            ".main-content"
        ];
        
        // Try priority selectors first
        for selector in &content_selectors {
            if let Some(content_nodes) = dom.query_selector(selector) {
                for node_handle in content_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        let content = node.inner_text(parser);
                        if content.trim().len() > 30 {  // Reduced from 100 to 30 for better coverage
                            return content.to_string();
                        }
                    }
                }
            }
        }
        
        // For index pages and listings, try broader selectors
        let broad_selectors = [
            ".container",
            ".wrapper",
            "#wrapper",
            ".page",
            ".page-content",
            "body > div",
            "body > main",
            "body > section"
        ];
        
        for selector in &broad_selectors {
            if let Some(content_nodes) = dom.query_selector(selector) {
                for node_handle in content_nodes {
                    if let Some(node) = node_handle.get(parser) {
                        let content = self.clean_body_text(&node.inner_text(parser));
                        if content.trim().len() > 30 {  // Reduced from 100 to 30
                            return content;
                        }
                    }
                }
            }
        }
        
        // Fallback to body text (more permissive for index pages)
        if let Some(body_nodes) = dom.query_selector("body") {
            for node_handle in body_nodes {
                if let Some(node) = node_handle.get(parser) {
                    let content = self.clean_body_text(&node.inner_text(parser));
                    // For index pages, accept any content > 20 characters (was 50)
                    if content.trim().len() > 20 {
                        return content;
                    }
                }
            }
        }
        
        String::new()
    }
    
    fn clean_body_text(&self, text: &str) -> String {
        // Remove navigation and boilerplate content but be less aggressive
        let lines: Vec<&str> = text.lines()
            .filter(|line| {
                let line_lower = line.to_lowercase();
                let line_trim = line.trim();
                
                // Skip empty lines
                if line_trim.is_empty() {
                    return false;
                }
                
                // Keep lines that are likely content (be more permissive)
                if line_trim.len() > 3 {
                    // Only filter obvious navigation/boilerplate
                    !line_lower.contains("privacy policy") &&
                    !line_lower.contains("terms of service") &&
                    !line_lower.contains("all rights reserved") &&
                    !line_lower.starts_with("©") &&
                    !line_lower.starts_with("copyright") &&
                    !(line_lower.contains("menu") && line_trim.len() < 20) &&
                    !(line_lower.contains("navigation") && line_trim.len() < 30) &&
                    line_trim.len() < 500  // Avoid very long lines that might be code/data
                } else {
                    false
                }
            })
            .collect();
        
        lines.join("\n")
    }
    
    fn annotate_technical_content(&self, content: &str) -> String {
        if content.len() > 50000 {
            return content.to_string(); // Skip very large content for performance
        }
        
        let mut annotated = content.to_string();
        
        // Annotate API references
        annotated = self.api_pattern.replace_all(&annotated, "# <api>$0</api>").to_string();
        
        // Annotate function calls
        annotated = self.function_pattern.replace_all(&annotated, "# <fn>$0</fn>").to_string();
        
        // Annotate technical keywords
        annotated = self.tech_pattern.replace_all(&annotated, "# <tech>$0</tech>").to_string();
        
        annotated
    }
    
    fn calculate_comprehensive_metrics(&self, document: &mut ProcessedDocument) {
        let content = &document.main_content;
        if content.is_empty() {
            return;
        }
        
        // Basic text metrics
        let words: Vec<&str> = content.split_whitespace().collect();
        let sentences: Vec<&str> = content.split(&['.', '!', '?'][..]).collect();
        let paragraphs: Vec<&str> = content.split("

").filter(|p| !p.trim().is_empty()).collect();
        
        document.word_count = words.len();
        
        // Calculate semantic info
        document.semantic_info = SemanticInfo {
            word_count: words.len(),
            sentence_count: sentences.len(),
            paragraph_count: paragraphs.len(),
            reading_time_minutes: words.len() as f32 / 200.0, // 200 WPM
            content_quality_score: self.calculate_quality_score(content, &document.headings),
            is_technical_content: false, // Will be set later
            headings_count: document.headings.len(),
            images_count: document.images.len(),
            links_count: document.links.len(),
            technical_score: self.calculate_technical_score(content),
            avg_sentence_length: if sentences.len() > 0 { words.len() as f32 / sentences.len() as f32 } else { 0.0 },
            content_density: content.replace(' ', "").len() as f32 / content.len().max(1) as f32,
        };
        
        document.content_quality_score = document.semantic_info.content_quality_score;
    }
    
    fn calculate_quality_score(&self, content: &str, headings: &[Heading]) -> f32 {
        let mut score: f32 = 5.0; // Base score
        
        // Length bonus
        let word_count = content.split_whitespace().count();
        if word_count > 300 {
            score += 1.0;
        }
        if word_count > 1000 {
            score += 1.0;
        }
        
        // Structure bonus
        if !headings.is_empty() {
            score += 1.0;
        }
        if headings.len() > 3 {
            score += 0.5;
        }
        
        // Technical content bonus
        if self.tech_pattern.is_match(content) {
            score += 1.0;
        }
        
        score.min(10.0)
    }
    
    fn calculate_technical_score(&self, content: &str) -> f32 {
        let mut score = 0.0;
        
        // API references
        score += self.api_pattern.find_iter(content).count() as f32 * 0.5;
        
        // Function patterns
        score += self.function_pattern.find_iter(content).count() as f32 * 0.3;
        
        // Technical keywords
        score += self.tech_pattern.find_iter(content).count() as f32 * 0.2;
        
        score.min(10.0)
    }
    
    fn is_technical_content(&self, document: &ProcessedDocument) -> bool {
        // Check technical score
        if document.semantic_info.technical_score > 2.0 {
            return true;
        }
        
        // Check if content has technical annotations
        if document.main_content.contains("# <api>") ||
           document.main_content.contains("# <fn>") ||
           document.main_content.contains("# <tech>") {
            return true;
        }
        
        // Check headings for technical terms
        for heading in &document.headings {
            if self.tech_pattern.is_match(&heading.text) {
                return true;
            }
        }
        
        false
    }
    
    fn extract_keywords_from_content(&self, content: &str, max_keywords: usize) -> Vec<String> {
        use std::collections::HashMap;
        
        if content.is_empty() {
            return Vec::new();
        }
        
        // Extract words (minimum 3 characters)
        let word_regex = Regex::new(r"\b[a-zA-Z]{3,}\b").unwrap();
        let words: Vec<String> = word_regex
            .find_iter(&content.to_lowercase())
            .map(|m| m.as_str().to_string())
            .collect();
        
        // Filter out stop words and common patterns
        let stop_words = [
            "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "man", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use",
            "www", "http", "html", "css", "php", "com", "org", "net", "amp", "nbsp", "quot", "copy", "reg", "trade", "hellip", "ndash", "mdash"
        ];
        
        let filtered_words: Vec<String> = words
            .into_iter()
            .filter(|word| {
                word.len() >= 4 && 
                !word.chars().all(|c| c.is_ascii_digit()) &&
                !stop_words.contains(&word.as_str()) &&
                !word.starts_with("http") &&
                !word.starts_with("www")
            })
            .collect();
        
        // Count frequency
        let mut word_freq: HashMap<String, usize> = HashMap::new();
        for word in filtered_words {
            *word_freq.entry(word).or_insert(0) += 1;
        }
        
        // Sort by frequency and take top keywords
        let mut keywords: Vec<(String, usize)> = word_freq.into_iter().collect();
        keywords.sort_by(|a, b| b.1.cmp(&a.1));
        
        keywords
            .into_iter()
            .take(max_keywords)
            .filter(|(_, freq)| *freq >= 2)  // Only include words that appear at least twice
            .map(|(word, _)| word)
            .collect()
    }
    
    fn parse_date_string(&self, date_str: &str) -> Option<String> {
        if date_str.is_empty() {
            return None;
        }
        
        let trimmed = date_str.trim();
        if trimmed.is_empty() {
            return None;
        }
        
        // Try to parse various date formats and normalize to ISO 8601 with Z suffix
        
        // 1. ISO 8601 formats (already correct)
        if let Ok(dt) = DateTime::parse_from_rfc3339(trimmed) {
            let utc_dt = dt.with_timezone(&Utc);
            return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
        }
        
        // 2. RFC 2822 format (e.g., "Fri, 22 Aug 2025 15:05:20 GMT")
        if let Ok(dt) = DateTime::parse_from_rfc2822(trimmed) {
            let utc_dt = dt.with_timezone(&Utc);
            return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
        }
        
        // 3. Common web formats with timezone
        let web_formats_with_tz = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %z",
            "%b %d, %Y %H:%M:%S %z",
        ];
        
        for format in &web_formats_with_tz {
            if let Ok(dt) = DateTime::parse_from_str(trimmed, format) {
                let utc_dt = dt.with_timezone(&Utc);
                return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
            }
        }
        
        // 4. Naive datetime formats (assume UTC)
        let naive_formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%m-%d-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%b %d, %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%B %d, %Y %H:%M:%S",
            "%d %B %Y %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
        ];
        
        for format in &naive_formats {
            if let Ok(ndt) = NaiveDateTime::parse_from_str(trimmed, format) {
                let utc_dt = Utc.from_utc_datetime(&ndt);
                return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
            }
        }
        
        // 5. US format with AM/PM (e.g., "7/29/2025, 9:28:40 AM")
        let am_pm_formats = [
            "%m/%d/%Y, %I:%M:%S %p",
            "%m/%d/%Y %I:%M:%S %p",
            "%d/%m/%Y, %I:%M:%S %p",
            "%d/%m/%Y %I:%M:%S %p",
            "%m-%d-%Y, %I:%M:%S %p",
            "%m-%d-%Y %I:%M:%S %p",
            "%b %d, %Y, %I:%M:%S %p",
            "%B %d, %Y, %I:%M:%S %p",
        ];
        
        for format in &am_pm_formats {
            if let Ok(ndt) = NaiveDateTime::parse_from_str(trimmed, format) {
                let utc_dt = Utc.from_utc_datetime(&ndt);
                return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
            }
        }
        
        // 6. Date-only formats (set time to 00:00:00 UTC)
        let date_only_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y", 
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%b %d, %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%d %B %Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%Y.%m.%d",
        ];
        
        for format in &date_only_formats {
            if let Ok(nd) = NaiveDate::parse_from_str(trimmed, format) {
                if let Some(ndt) = nd.and_hms_opt(0, 0, 0) {
                    let utc_dt = Utc.from_utc_datetime(&ndt);
                    return Some(utc_dt.format("%Y-%m-%dT%H:%M:%SZ").to_string());
                }
            }
        }
        
        // 7. Try to extract date from mixed content using regex
        if let Some(extracted) = self.extract_date_from_text(trimmed) {
            return self.parse_date_string(&extracted);
        }
        
        // If all parsing fails, return None (don't pass invalid dates)
        None
    }
    
    /// Extract date strings from mixed content using regex patterns
    fn extract_date_from_text(&self, text: &str) -> Option<String> {
        // Enhanced regex patterns to match various date formats
        let patterns = [
            // ISO-like formats
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:?\d{2})?",
            r"\d{4}-\d{2}-\d{2}",
            
            // US formats
            r"\d{1,2}/\d{1,2}/\d{4}(?:,?\s+\d{1,2}:\d{2}:\d{2}(?:\s+[AP]M)?)?",
            r"\d{1,2}-\d{1,2}-\d{4}(?:,?\s+\d{1,2}:\d{2}:\d{2}(?:\s+[AP]M)?)?",
            
            // European formats  
            r"\d{1,2}\.\d{1,2}\.\d{4}(?:,?\s+\d{1,2}:\d{2}:\d{2})?",
            
            // Month name formats
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}(?:,?\s+\d{1,2}:\d{2}:\d{2}(?:\s+[AP]M)?)?",
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}(?:,?\s+\d{1,2}:\d{2}:\d{2}(?:\s+[AP]M)?)?",
            
            // RFC 2822 style
            r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+(?:GMT|UTC|[+-]\d{4})",
        ];
        
        for pattern_str in &patterns {
            if let Ok(regex) = Regex::new(pattern_str) {
                if let Some(matched) = regex.find(text) {
                    return Some(matched.as_str().to_string());
                }
            }
        }
        
        None
    }
    
    // Helper function to clean and normalize date strings
    fn clean_date_string(&self, date_str: &str) -> String {
        if date_str.is_empty() {
            return String::new();
        }
        
        // Remove common prefixes and suffixes
        let cleaned = date_str
            .trim()
            .replace("Published:", "")
            .replace("Last modified:", "")
            .replace("Updated:", "")
            .replace("Date:", "")
            .replace("Created:", "")
            .replace("Modified:", "")
            .trim()
            .to_string();
        
        // Try to parse and return ISO 8601 format, or empty string if invalid
        self.parse_date_string(&cleaned).unwrap_or_default()
    }
    
    // Helper function to generate anchor IDs from text
    fn generate_anchor_id(&self, text: &str) -> String {
        text.to_lowercase()
            .chars()
            .filter(|c| c.is_alphanumeric() || c.is_whitespace() || *c == '-')
            .collect::<String>()
            .split_whitespace()
            .collect::<Vec<&str>>()
            .join("-")
            .chars()
            .take(50) // Limit length
            .collect()
    }
    
    // Helper function to extract metadata from JSON-LD
    fn extract_from_json_ld(&self, json_value: &serde_json::Value, document: &mut ProcessedDocument) {
        // Handle both single objects and arrays
        let objects = if json_value.is_array() {
            json_value.as_array().unwrap()
        } else {
            &vec![json_value.clone()]
        };
        
        for obj in objects {
            if let Some(obj_map) = obj.as_object() {
                // Extract dates with proper validation
                if let Some(published) = obj_map.get("datePublished").and_then(|v| v.as_str()) {
                    if document.published_date.is_none() && !published.is_empty() {
                        let cleaned_date = self.clean_date_string(published);
                        if !cleaned_date.is_empty() {
                            document.published_date = Some(cleaned_date);
                        }
                    }
                }
                
                if let Some(modified) = obj_map.get("dateModified").and_then(|v| v.as_str()) {
                    if document.modified_date.is_none() && !modified.is_empty() {
                        let cleaned_date = self.clean_date_string(modified);
                        if !cleaned_date.is_empty() {
                            document.modified_date = Some(cleaned_date);
                        }
                    }
                }
                
                // Extract categories/genres
                if let Some(genre) = obj_map.get("genre").and_then(|v| v.as_str()) {
                    if !document.content_categories.contains(&genre.to_lowercase()) {
                        document.content_categories.push(genre.to_lowercase());
                    }
                }
                
                if let Some(category) = obj_map.get("articleSection").and_then(|v| v.as_str()) {
                    if !document.content_categories.contains(&category.to_lowercase()) {
                        document.content_categories.push(category.to_lowercase());
                    }
                }
                
                // Extract keywords from JSON-LD
                if let Some(keywords) = obj_map.get("keywords") {
                    let extracted_keywords = match keywords {
                        serde_json::Value::String(s) => {
                            s.split(',').map(|k| k.trim().to_lowercase()).collect()
                        }
                        serde_json::Value::Array(arr) => {
                            arr.iter()
                                .filter_map(|v| v.as_str())
                                .map(|k| k.trim().to_lowercase())
                                .collect()
                        }
                        _ => vec![]
                    };
                    
                    for keyword in extracted_keywords {
                        if !keyword.is_empty() && keyword.len() >= 3 && !document.keywords.contains(&keyword) {
                            document.keywords.push(keyword);
                        }
                    }
                }
            }
        }
    }
}
