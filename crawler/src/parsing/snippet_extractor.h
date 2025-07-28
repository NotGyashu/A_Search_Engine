#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <cstddef>

/**
 * 🔧 INTELLIGENT SNIPPET EXTRACTION
 * Modular design for high-quality preview snippets
 */

namespace SnippetExtraction {

struct SnippetConfig {
    // Content filtering with better priorities - enhanced for Google-like quality
    std::vector<std::string> priority_tags = {"article", "main", "[role=\"main\"]", "section", "div.content", "div.post", "div.article", "div.entry-content"};
    std::vector<std::string> content_tags = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li", "dd", "div"};
    std::vector<std::string> exclude_tags = {"header", "nav", "aside", "footer", "script", "style", "meta", "noscript", "form", "button", "input"};
    std::vector<std::string> boilerplate_selectors = {"menu", "sidebar", "advertisement", "ads", "cookie", "social", "share", "subscribe", "newsletter", "breadcrumb"};
    
    // Google-like snippet parameters
    size_t max_snippet_length = 320;  // Google uses ~320 chars
    size_t min_sentence_length = 30;  // Longer minimum for quality
    size_t target_sentences = 2;      // Focus on 1-2 high-quality sentences
    size_t max_sentences = 3;
    size_t min_words_per_sentence = 6;
    
    // Enhanced language heuristics for Google-like quality
    float min_alphabetic_ratio = 0.80f;  // Higher quality threshold
    size_t min_meaningful_words = 10;    // More substantial content
    size_t max_repeated_words = 2;       // Less tolerance for repetition
    float min_sentence_complexity = 0.6f; // Prefer complex sentences
    
    // Content quality filters - stricter for Google-like results
    bool prefer_complete_sentences = true;
    bool avoid_link_heavy_content = true;
    bool skip_short_paragraphs = true;
    bool require_proper_punctuation = true;
    bool avoid_all_caps = true;
    size_t min_paragraph_length = 60;
    size_t max_marketing_words = 3;      // Limit promotional language
    
    // Advanced text processing
    bool normalize_whitespace = true;
    bool remove_html_entities = true;
    bool preserve_sentence_boundaries = true;
    bool fix_spacing_issues = true;      // Fix "wordword" issues
    bool smart_sentence_ending = true;   // Ensure proper sentence endings
};

struct ExtractedSnippet {
    std::string text_snippet;
    std::string primary_language;
    float quality_score = 0.0f;
    float content_density = 0.0f;      // Ratio of content to boilerplate
    float readability_score = 0.0f;    // How readable the snippet is
    size_t source_tag_count = 0;
    size_t paragraph_count = 0;
    size_t sentence_count = 0;
    bool is_meaningful = false;
    bool has_main_content = false;      // Found in main content areas
    std::string extraction_method;      // Which method was used
};

/**
 * Abstract base class for snippet extraction
 * Enables plug-and-play architecture for different extraction strategies
 */
class SnippetExtractor {
public:
    virtual ~SnippetExtractor() = default;
    virtual ExtractedSnippet extract_snippet(const std::string& html_content,
                                            const std::string& url = "",
                                            const SnippetConfig& config = SnippetConfig{}) = 0;
    virtual void set_domain_config(const std::string& domain, const SnippetConfig& config) = 0;
};

class BasicSnippetExtractor : public SnippetExtractor {
private:
    std::unordered_map<std::string, SnippetConfig> domain_configs_;
    SnippetConfig default_config_;

    // Enhanced HTML/text processing helpers
    std::string extract_text_from_priority_tags(const std::string& html, const SnippetConfig& config) const;
    std::string extract_main_content(const std::string& html, const SnippetConfig& config) const;
    std::string extract_semantic_content(const std::string& html, const SnippetConfig& config) const;
    std::string normalize_text(const std::string& text, const SnippetConfig& config) const;
    std::string strip_html_tags_simple(const std::string& html) const;
    std::string extract_content_by_tag(const std::string& html, const std::string& tag) const;
    
    // Boilerplate detection and removal
    bool is_boilerplate_content(const std::string& text, const SnippetConfig& config) const;
    bool contains_navigation_patterns(const std::string& text) const;
    bool is_repetitive_content(const std::string& text, const SnippetConfig& config) const;
    std::string remove_boilerplate_sentences(const std::string& text, const SnippetConfig& config) const;
    
    // Enhanced content structure analysis
    std::vector<std::string> extract_paragraphs(const std::string& html, const SnippetConfig& config) const;
    std::vector<std::string> rank_paragraphs_by_quality(const std::vector<std::string>& paragraphs, const SnippetConfig& config) const;
    std::string extract_first_meaningful_paragraph(const std::string& html, const SnippetConfig& config) const;
    std::string extract_title_context(const std::string& html, const std::string& title, const SnippetConfig& config) const;
    float calculate_content_density(const std::string& text) const;
    float calculate_readability_score(const std::string& text) const;
    
    // Google-like content quality analysis
    bool is_marketing_heavy(const std::string& text, const SnippetConfig& config) const;
    bool has_proper_sentence_structure(const std::string& text) const;
    bool contains_meaningful_information(const std::string& text, const SnippetConfig& config) const;
    std::string fix_text_spacing(const std::string& text) const;
    std::string create_google_like_snippet(const std::string& text, const SnippetConfig& config) const;
    std::string remove_marketing_fluff(const std::string& text, const SnippetConfig& config) const;
    bool is_link_heavy(const std::string& text) const;

protected:

    // Quality heuristics
    float calculate_alphabetic_ratio(const std::string& text) const;
    size_t count_meaningful_words(const std::string& text) const;
    bool has_sentence_structure(const std::string& text) const;

    // Sentence utilities
    std::vector<std::string> extract_sentences(const std::string& text, const SnippetConfig& config) const;
    std::string build_snippet_from_sentences(const std::vector<std::string>& sentences, const SnippetConfig& config) const;

    // Config helpers
    SnippetConfig get_config_for_domain(const std::string& domain) const;
    void replace_all(std::string& str, const std::string& from, const std::string& to) const;

public:
    BasicSnippetExtractor();
    ~BasicSnippetExtractor() override = default;
    ExtractedSnippet extract_snippet(const std::string& html_content,
                                   const std::string& url = "",
                                   const SnippetConfig& config = SnippetConfig{}) override;
    void set_domain_config(const std::string& domain, const SnippetConfig& config) override;
    void print_extraction_stats() const;
};

class SnippetExtractorFactory {
public:
    enum class ExtractorType {
        BASIC,
    };
    static std::unique_ptr<SnippetExtractor> create_extractor(ExtractorType type = ExtractorType::BASIC);
};

} // namespace SnippetExtraction
