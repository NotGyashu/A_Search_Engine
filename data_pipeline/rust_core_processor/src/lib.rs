use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use regex::Regex;
use once_cell::sync::Lazy;

mod extractor;
mod cleaner;
mod types;
mod language_detector;

use extractor::OptimizedExtractor;
use cleaner::FastCleaner;
use types::ProcessedDocument;
use language_detector::FastLanguageDetector;

// Global regex patterns compiled once
static WHITESPACE_REGEX: Lazy<Regex> = Lazy::new(|| Regex::new(r"\s+").unwrap());
static URL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r#"https?://[^\s<>"']+"#).unwrap()
});

// Regex patterns for removing unwanted HTML tags and their content
static SCRIPT_TAG_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?s)<script[^>]*>.*?</script>").unwrap()
});
static STYLE_TAG_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?s)<style[^>]*>.*?</style>").unwrap()
});
static NOSCRIPT_TAG_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?s)<noscript[^>]*>.*?</noscript>").unwrap()
});
static NAV_TAG_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?s)<nav[^>]*>.*?</nav>").unwrap()
});
static FOOTER_TAG_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?s)<footer[^>]*>.*?</footer>").unwrap()
});
static HEADER_TAG_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?s)<header[^>]*>.*?</header>").unwrap()
});

/// Remove unwanted HTML tags and their content before parsing
fn remove_unwanted_tags(html: &str) -> String {
    let mut cleaned = html.to_string();
    
    // Remove script tags and all their content
    cleaned = SCRIPT_TAG_REGEX.replace_all(&cleaned, "").to_string();
    
    // Remove style tags and all their content (this solves the CSS problem!)
    cleaned = STYLE_TAG_REGEX.replace_all(&cleaned, "").to_string();
    
    // Remove noscript tags and content
    cleaned = NOSCRIPT_TAG_REGEX.replace_all(&cleaned, "").to_string();
    
    // Remove navigation elements (often contain menu noise)
    cleaned = NAV_TAG_REGEX.replace_all(&cleaned, "").to_string();
    
    // Remove headers and footers (often contain site-wide navigation)
    cleaned = HEADER_TAG_REGEX.replace_all(&cleaned, "").to_string();
    cleaned = FOOTER_TAG_REGEX.replace_all(&cleaned, "").to_string();
    
    cleaned
}

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
                
            // Set basic fields
            dict.set_item("main_content", &doc.main_content)?;
            dict.set_item("title", &doc.title)?;
            dict.set_item("description", &doc.description)?;
            dict.set_item("language", &doc.language)?;
            dict.set_item("keywords", doc.keywords.to_object(py))?;
            dict.set_item("structured_meta", doc.structured_meta.to_object(py))?;
            dict.set_item("headings", doc.headings.to_object(py))?;
            dict.set_item("primary_image", doc.primary_image.to_object(py))?;
            dict.set_item("favicon", doc.favicon.to_object(py))?;
            dict.set_item("author_name", doc.author_name.to_object(py))?;
            dict.set_item("published_date", doc.published_date.to_object(py))?;
            dict.set_item("modified_date", doc.modified_date.to_object(py))?;
            dict.set_item("canonical_url", doc.canonical_url.to_object(py))?;
            dict.set_item("semantic_info", doc.semantic_info.to_object(py))?;
            dict.set_item("text_chunks_with_context", doc.text_chunks_with_context.to_object(py))?;
            dict.set_item("word_count", &doc.word_count)?;
            dict.set_item("content_quality_score", &doc.content_quality_score)?;
            dict.set_item("is_technical_content", &doc.is_technical_content)?;                Ok(dict.into())
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
    // ⚡ CRITICAL: Remove unwanted tags BEFORE parsing to prevent CSS/script content from being extracted
    let cleaned_html = remove_unwanted_tags(&html_content);
    
    // Parse the cleaned HTML using the ultra-fast tl parser
    let _dom = tl::parse(&cleaned_html, tl::ParserOptions::default())?;
    
    // Initialize processors
    let extractor = OptimizedExtractor::new();
    let cleaner = FastCleaner::new();
    
    // Extract all content from the cleaned HTML in one pass
    let mut doc = extractor.extract_content(&cleaned_html, &url);
    
    // ⚡ CLEAN ALL DATES using the FastCleaner for OpenSearch compatibility
    // Date fields are already normalized in the optimized extractor
    
    // Clean structured meta dates if present (simple structure now)
    // No complex JSON cleaning needed since we only store essential fields
    
    // Ultra-fast language detection using Rust
    if let Some(detected_lang) = FastLanguageDetector::detect_language(&cleaned_html, &url) {
        doc.language = detected_lang;
    }
    
    // Early filtering: skip non-English content for English-only search engine
    if doc.language != "en" && !FastLanguageDetector::is_english(&doc.main_content, &url) {
        // Return minimal document for non-English content
        doc.main_content = String::new();
        doc.text_chunks_with_context = Vec::new();
        return Ok(doc);
    }
    
    // Clean and process the text (only for English content)
    doc.main_content = cleaner.clean_text(&doc.main_content);
    doc.description = cleaner.clean_description(&doc.description);
    
    // 🧹 CRITICAL: Clean ALL chunks using FastCleaner for proper noise removal
    for chunk in &mut doc.text_chunks_with_context {
        chunk.text_chunk = cleaner.clean_text(&chunk.text_chunk);
    }
    
    // Filter out chunks that became too small or empty after cleaning (reduced minimum length)
    doc.text_chunks_with_context.retain(|chunk| {
        !chunk.text_chunk.is_empty() && chunk.text_chunk.len() >= 25  // Reduced from 50 to 25
    });
    
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
    if doc.primary_image.is_some() {
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
