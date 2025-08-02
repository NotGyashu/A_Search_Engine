#pragma once

#include <string>
#include <vector>
#include <string_view>

/**
 * High-performance HTML document parser - REGEX-FREE
 * Uses fast manual parsing with std::string_view for zero-copy operations
 * Thread-safe and optimized for multi-threaded web crawling
 */
class HtmlDocument {
private:
    std::string html_content_;
    mutable std::string cached_title_;
    mutable std::string cached_meta_description_;
    mutable std::string cached_clean_text_;

    // Fast manual parsing helpers (no regex)
    std::string remove_scripts_and_styles_fast(std::string_view html) const;
    std::string strip_html_tags_fast(std::string_view html) const;
    std::string clean_extracted_text_fast(std::string_view text) const;
    std::string normalize_whitespace_fast(std::string_view text) const;

    // Fast tag extraction using string operations
    std::string extract_tag_content_fast(std::string_view html, std::string_view tag_name) const;
    std::string extract_meta_content_fast(std::string_view html, std::string_view name) const;
    
    // Advanced content extraction methods (regex-free)
    std::string extract_main_content_heuristic_fast(std::string_view html) const;
    std::string extract_paragraph_content_fast(std::string_view html) const;
    bool is_boilerplate_content_fast(std::string_view text) const;
    bool is_navigation_content_fast(std::string_view text) const;

    // Centralized parsing method called by the constructor
    void parse();

    // Fast utility helpers
    static size_t find_case_insensitive(std::string_view haystack, std::string_view needle, size_t start = 0);
    static bool starts_with_case_insensitive(std::string_view str, std::string_view prefix);
    static std::string_view trim_whitespace(std::string_view str);

public:
    // Constructor uses move semantics for efficiency
    explicit HtmlDocument(const std::string& html_content);

    // Basic extraction methods (now just return cached values)
    const std::string& getTitle() const;
    const std::string& getMetaDescription() const;
    std::string getMetaKeywords() const;
    const std::string& getCleanText() const;

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
    const std::string& getRawHtml() const;

    // Static utility methods (regex-free)
    static std::string resolveRelativeUrl(const std::string& base_url, const std::string& relative_url);
    static std::string extractDomain(const std::string& url);
    static bool isValidHtml(const std::string& content);
};