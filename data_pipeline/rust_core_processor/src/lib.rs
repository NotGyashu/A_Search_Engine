use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use regex::Regex;
use once_cell::sync::Lazy;

mod extractor;
mod cleaner;
mod types;
mod language_detector;

use extractor::FastExtractor;
use cleaner::FastCleaner;
use types::ProcessedDocument;
use language_detector::FastLanguageDetector;

// Global regex patterns compiled once
static WHITESPACE_REGEX: Lazy<Regex> = Lazy::new(|| Regex::new(r"\s+").unwrap());
static URL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r#"https?://[^\s<>"']+"#).unwrap()
});

/// Standalone ultra-fast language detection function
#[pyfunction]
fn detect_language_fast(text: String, url: String) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let detected_lang = FastLanguageDetector::detect_language(&text, &url);
        Ok(detected_lang.to_object(py))
    })
}

/// Check if content is English (optimized for filtering)
#[pyfunction] 
fn is_english_fast(text: String, url: String) -> PyResult<bool> {
    Ok(FastLanguageDetector::is_english(&text, &url))
}

/// Get detailed language detection information
#[pyfunction]
fn get_language_info_fast(text: String, url: String) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let (detected_lang, confidence, is_english_domain) = FastLanguageDetector::get_language_info(&text, &url);
        
        let dict = PyDict::new_bound(py);
        dict.set_item("detected_language", detected_lang)?;
        dict.set_item("confidence", confidence)?;
        dict.set_item("is_english_domain", is_english_domain)?;
        
        Ok(dict.to_object(py))
    })
}

/// Main function exposed to Python - processes HTML and returns structured data
#[pyfunction]
fn process_html(html_content: String, url: String) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let result = internal_process_html(html_content, url);
        
        match result {
            Ok(doc) => {
                let dict = PyDict::new_bound(py);
                
                // Core content
                dict.set_item("main_content", &doc.main_content)?;
                dict.set_item("title", &doc.title)?;
                dict.set_item("description", &doc.description)?;
                dict.set_item("language", &doc.language)?;
                
                // Metadata
                dict.set_item("keywords", doc.keywords)?;
                
                // Convert complex types to Python objects
                let headings: Vec<PyObject> = doc.headings.iter()
                    .map(|h| h.to_object(py))
                    .collect();
                dict.set_item("headings", headings)?;
                
                let images: Vec<PyObject> = doc.images.iter()
                    .map(|i| i.to_object(py))
                    .collect();
                dict.set_item("images", images)?;
                
                let links: Vec<PyObject> = doc.links.iter()
                    .map(|l| l.to_object(py))
                    .collect();
                dict.set_item("links", links)?;
                
                // Table of contents
                let toc: Vec<PyObject> = doc.table_of_contents.iter()
                    .map(|h| h.to_object(py))
                    .collect();
                dict.set_item("table_of_contents", toc)?;
                
                // Content metrics
                dict.set_item("word_count", doc.word_count)?;
                dict.set_item("content_quality_score", doc.content_quality_score)?;
                dict.set_item("is_technical_content", doc.is_technical_content)?;
                dict.set_item("content_categories", doc.content_categories)?;
                
                // Metadata
                dict.set_item("canonical_url", &doc.canonical_url)?;
                dict.set_item("published_date", doc.published_date)?;
                dict.set_item("modified_date", doc.modified_date)?;
                
                // Author info
                dict.set_item("author_info", doc.author_info.to_object(py))?;
                
                // Text chunks for indexing
                dict.set_item("text_chunks", doc.text_chunks)?;
                
                // Structured data - convert to Python objects
                dict.set_item("structured_data", doc.structured_data.to_object(py))?;
                
                // Social media metadata
                dict.set_item("meta_tags", doc.meta_tags)?;
                dict.set_item("open_graph", doc.open_graph)?;
                dict.set_item("twitter_cards", doc.twitter_cards)?;
                
                // Icons
                dict.set_item("icons", doc.icons)?;
                
                // Semantic info  
                dict.set_item("semantic_info", doc.semantic_info.to_object(py))?;
                
                Ok(dict.into())
            }
            Err(e) => {
                let dict = PyDict::new_bound(py);
                dict.set_item("error", format!("Processing failed: {}", e))?;
                dict.set_item("main_content", "")?;
                dict.set_item("title", "")?;
                dict.set_item("description", "")?;
                dict.set_item("keywords", Vec::<String>::new())?;
                dict.set_item("text_chunks", Vec::<String>::new())?;
                Ok(dict.into())
            }
        }
    })
}

/// Internal processing function that does the actual work
fn internal_process_html(html_content: String, url: String) -> Result<ProcessedDocument, Box<dyn std::error::Error>> {
    // Parse HTML using the ultra-fast tl parser
    let dom = tl::parse(&html_content, tl::ParserOptions::default())?;
    
    // Initialize processors
    let extractor = FastExtractor::new();
    let cleaner = FastCleaner::new();
    
    // Extract all content in one pass
    let mut doc = extractor.extract_content(&html_content, &url);
    
    // ⚡ CLEAN ALL DATES using the FastCleaner for OpenSearch compatibility
    // Clean main date fields
    if let Some(ref date) = doc.published_date {
        doc.published_date = cleaner.normalize_date(date);
    }
    if let Some(ref date) = doc.modified_date {
        doc.modified_date = cleaner.normalize_date(date);
    }
    
    // Clean all dates in structured_data
    for json_ld in &mut doc.structured_data.json_ld {
        match json_ld {
            serde_json::Value::String(json_str) => {
                if let Some(cleaned) = cleaner.clean_json_dates(json_str) {
                    *json_ld = serde_json::Value::String(cleaned);
                }
            }
            value => {
                cleaner.clean_structured_data_dates(value);
            }
        }
    }
    
    // Clean dates in microdata
    for microdata in &mut doc.structured_data.microdata {
        cleaner.clean_hashmap_dates(microdata);
    }
    
    // Clean dates in rdfa
    for rdfa in &mut doc.structured_data.rdfa {
        cleaner.clean_hashmap_dates(rdfa);
    }
    
    // Ultra-fast language detection using Rust
    if let Some(detected_lang) = FastLanguageDetector::detect_language(&html_content, &url) {
        doc.language = detected_lang;
    }
    
    // Early filtering: skip non-English content for English-only search engine
    if doc.language != "en" && !FastLanguageDetector::is_english(&doc.main_content, &url) {
        // Return minimal document for non-English content
        doc.main_content = String::new();
        doc.text_chunks = Vec::new();
        return Ok(doc);
    }
    
    // Clean and process the text (only for English content)
    doc.main_content = cleaner.clean_text(&doc.main_content);
    doc.description = cleaner.clean_description(&doc.description);
    
    // Generate text chunks for search indexing
    doc.text_chunks = cleaner.create_chunks(&doc.main_content, 2500, 100);
    
    // Calculate content quality metrics
    doc.word_count = doc.main_content.split_whitespace().count();
    doc.content_quality_score = calculate_content_quality(&doc);
    doc.is_technical_content = detect_technical_content(&doc.main_content);
    
    Ok(doc)
}

/// Calculate content quality score
fn calculate_content_quality(doc: &ProcessedDocument) -> f32 {
    let mut score = 0.0;
    
    // Length scoring
    let word_count = doc.word_count as f32;
    if word_count > 100.0 {
        score += (word_count / 1000.0).min(3.0);
    }
    
    // Structure scoring
    if !doc.headings.is_empty() {
        score += 1.0;
    }
    
    if doc.headings.len() > 2 {
        score += 0.5;
    }
    
    // Content diversity
    if !doc.images.is_empty() {
        score += 0.5;
    }
    
    if !doc.description.is_empty() && doc.description.len() > 50 {
        score += 1.0;
    }
    
    // Technical content bonus
    if doc.is_technical_content {
        score += 0.5;
    }
    
    score.min(10.0)
}

/// Detect if content is technical in nature
fn detect_technical_content(text: &str) -> bool {
    let technical_keywords = [
        "api", "function", "class", "method", "property", "parameter",
        "interface", "implementation", "algorithm", "data structure",
        "programming", "code", "software", "technology", "technical"
    ];
    
    let text_lower = text.to_lowercase();
    let mut technical_count = 0;
    
    for keyword in &technical_keywords {
        if text_lower.contains(keyword) {
            technical_count += 1;
        }
    }
    
    // Consider technical if 3+ technical terms or high density
    technical_count >= 3 || (technical_count as f32 / text.len() as f32) > 0.0001
}

/// Python module definition
#[pymodule]
fn rust_core_processor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_html, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language_fast, m)?)?;
    m.add_function(wrap_pyfunction!(is_english_fast, m)?)?;
    m.add_function(wrap_pyfunction!(get_language_info_fast, m)?)?;
    Ok(())
}
