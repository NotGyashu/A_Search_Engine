#pragma once
#include <string>
#include <vector>
#include <unordered_set>
#include <algorithm>
#include <regex>
#include <cstdint> 

/**
 * 🌐 ULTRA-FAST LANGUAGE DETECTION
 * Zero-cost English detection for crawler
 * Uses pattern matching instead of heavy ML models
 */
class FastLanguageDetector {
private:
    // Most common English words (sorted by frequency)
    static const std::unordered_set<std::string> COMMON_ENGLISH_WORDS;
    
    // English-specific patterns
    static const std::vector<std::string> ENGLISH_PATTERNS;
    
    // HTML lang attribute regex
    static const std::regex HTML_LANG_REGEX;
    
public:
    /**
     * Fast English detection (< 1ms per page)
     * @param html Raw HTML content
     * @param url Page URL for additional context
     * @return true if likely English, false otherwise
     */
    static bool is_english_content(const std::string& html, const std::string& url = "");
    
    /**
     * Extract language from HTML lang attribute
     * @param html Raw HTML content
     * @return language code if found, empty string otherwise
     */
    static std::string extract_html_lang(const std::string& html);
    
    /**
     * Check if domain is likely English-speaking
     * @param url Page URL
     * @return true if English-speaking domain
     */
    static bool is_english_domain(const std::string& url);
    
private:
    /**
     * Count English words in text sample
     * @param text Text to analyze
     * @param max_words Maximum words to check (for performance)
     * @return ratio of English words found
     */
    static float calculate_english_word_ratio(const std::string& text, int max_words = 100);
    
    /**
     * Check for non-English scripts (Arabic, Chinese, etc.)
     * @param html HTML content
     * @return true if non-English script detected
     */
    static bool has_non_english_script(const std::string& html);
    
    /**
     * Extract text sample from HTML for analysis
     * @param html HTML content
     * @return clean text sample
     */
    static std::string extract_text_sample(const std::string& html);

    static const std::vector<std::pair<uint32_t, uint32_t>> NON_ENGLISH_RANGES;
};
