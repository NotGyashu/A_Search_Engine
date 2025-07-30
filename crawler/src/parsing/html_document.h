#pragma once

#include <string>
#include <vector>
#include <regex>

/**
 * Standardized HTML document parser
 * Provides consistent methods for extracting common elements
 * Uses sophisticated text cleaning and extraction logic
 */
class HtmlDocument {
private:
    std::string html_content_;
    mutable std::string cached_title_;
    mutable std::string cached_meta_description_;
    mutable std::string cached_clean_text_;
    mutable bool title_extracted_ = false;
    mutable bool meta_description_extracted_ = false;
    mutable bool clean_text_extracted_ = false;
    
    // Static regex patterns for efficient parsing
    static std::regex title_regex_;
    static std::regex meta_description_regex_;
    static std::regex meta_keywords_regex_;
    static std::regex script_style_regex_;
    static std::regex tag_regex_;
    static std::regex whitespace_regex_;
    static std::regex multiple_spaces_regex_;
    
    // Helper methods for text extraction and cleaning
    std::string extract_text_between_tags(const std::string& start_tag, const std::string& end_tag) const;
    std::string remove_scripts_and_styles(const std::string& html) const;
    std::string strip_html_tags(const std::string& html) const;
    std::string clean_extracted_text(const std::string& text) const;
    std::string normalize_whitespace(const std::string& text) const;
    
    // Advanced content extraction methods
    std::string extract_main_content_heuristic(const std::string& html) const;
    std::string extract_paragraph_content(const std::string& html) const;
    bool is_boilerplate_content(const std::string& text) const;
    bool is_navigation_content(const std::string& text) const;

public:
    explicit HtmlDocument(const std::string& html_content);
    
    // Basic extraction methods
    std::string getTitle() const;
    std::string getMetaDescription() const;
    std::string getMetaKeywords() const;
    std::string getCleanText() const;
    
    // Advanced content extraction
    std::string getMainContent() const;
    std::string getFirstParagraph() const;
    std::string getSnippet(size_t max_length = 160) const;
    
    // Content analysis
    size_t getContentLength() const;
    size_t getWordCount() const;
    float getTextDensity() const;
    bool hasValidStructure() const;
    bool isContentRich() const;
    
    // Language detection helpers
    std::string detectLanguage() const;
    bool isEnglishContent() const;
    
    // Link extraction
    std::vector<std::string> extractLinks(const std::string& base_url = "") const;
    std::vector<std::string> extractInternalLinks(const std::string& domain) const;
    
    // Utility methods
    bool isEmpty() const;
    std::string getRawHtml() const;
    
    // Static utility methods
    static std::string resolveRelativeUrl(const std::string& base_url, const std::string& relative_url);
    static std::string extractDomain(const std::string& url);
    static bool isValidHtml(const std::string& content);
};
