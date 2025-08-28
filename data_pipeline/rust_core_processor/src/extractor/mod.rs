pub mod metadata_extractor;
pub mod optimized;
pub mod main_content_extractor;
pub use optimized::OptimizedExtractor;

// Re-export for compatibility  
pub fn extract_all_metadata(html: &str, base_url: &str) -> crate::types::ProcessedDocument {
    let extractor = OptimizedExtractor::new();
    extractor.extract_content(html, base_url)
}
