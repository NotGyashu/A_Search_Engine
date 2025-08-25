mod optimized;
pub use optimized::OptimizedExtractor;

// Re-export for compatibility  
pub fn extract_all_metadata(html: &str, base_url: &str) -> crate::types::ProcessedDocument {
    let extractor = OptimizedExtractor::new();
    extractor.extract_content(html, base_url)
}
