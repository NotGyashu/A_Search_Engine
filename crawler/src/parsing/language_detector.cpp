#include "language_detector.h"
#include <sstream>
#include <cctype>
#include <algorithm>
#include <cstdint>

// Most common English words (top 100) - unchanged
const std::unordered_set<std::string> FastLanguageDetector::COMMON_ENGLISH_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", 
    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", 
    "how", "man", "new", "now", "old", "see", "two", "way", "who", "boy", 
    "did", "its", "let", "put", "say", "she", "too", "use", "about", "after", 
    "again", "also", "been", "before", "being", "between", "both", "called", 
    "came", "come", "could", "each", "find", "first", "from", "good", "great", 
    "have", "here", "into", "just", "know", "like", "long", "look", "make", 
    "many", "more", "most", "move", "much", "must", "name", "need", "number", 
    "only", "other", "over", "part", "place", "right", "same", "should", 
    "show", "since", "some", "such", "take", "than", "that", "their", "them", 
    "there", "these", "they", "thing", "think", "this", "those", "through", 
    "time", "under", "very", "want", "water", "well", "were", "what", "where", 
    "which", "while", "will", "with", "work", "would", "write", "year", "your"
};

// English-specific patterns - unchanged
const std::vector<std::string> FastLanguageDetector::ENGLISH_PATTERNS = {
    "ing ", "tion", "the ", "and ", "for ", "are ", "but ", "not ", "you ",
    "all ", "can ", "had ", "her ", "was ", "one ", "our ", "out ", "day ",
    "get ", "has ", "him ", "his ", "how ", "man ", "new ", "now ", "old ",
    "see ", "two ", "way ", "who "
};

// Non-English script code point ranges
const std::vector<std::pair<uint32_t, uint32_t>> FastLanguageDetector::NON_ENGLISH_RANGES = {
    {0x4e00, 0x9fff},     // Chinese
    {0x3040, 0x309f},     // Hiragana (Japanese)
    {0x30a0, 0x30ff},     // Katakana (Japanese)
    {0x0600, 0x06ff},     // Arabic
    {0x0400, 0x04ff},     // Cyrillic
    {0x0590, 0x05ff},     // Hebrew
    {0x0e00, 0x0e7f},     // Thai
    {0x0900, 0x097f},     // Devanagari (Hindi)
    {0x0980, 0x09ff},     // Bengali
    {0x0a00, 0x0a7f},     // Gurmukhi (Punjabi)
    {0x0a80, 0x0aff},     // Gujarati
    {0x0b00, 0x0b7f},     // Oriya
    {0x0b80, 0x0bff},     // Tamil
    {0x0c00, 0x0c7f},     // Telugu
    {0x0c80, 0x0cff},     // Kannada
    {0x0d00, 0x0d7f},     // Malayalam
    {0x1100, 0x11ff},     // Hangul Jamo (Korean)
    {0xac00, 0xd7a3}      // Hangul Syllables (Korean)
};


bool FastLanguageDetector::is_english_content(const std::string& html, const std::string& url) {
    // 1. Check HTML lang attribute (fastest check) - unchanged
    std::string lang_attr = extract_html_lang(html);
    if (!lang_attr.empty()) {
        return lang_attr.substr(0, 2) == "en";
    }
    
    // 2. Check domain (second fastest) - unchanged
    if (!url.empty() && is_english_domain(url)) {
        return true;  // Trust English-speaking domains
    }
    
    // 3. Quick non-English script detection - FIXED IMPLEMENTATION
    if (has_non_english_script(html)) {
        return false;  // Immediate rejection
    }
    
    // 4. Extract text sample for analysis - unchanged
    std::string text_sample = extract_text_sample(html);
    if (text_sample.length() < 50) {
        return false;  // Too little text to analyze
    }
    
    // 5. English word ratio check - unchanged
    float english_ratio = calculate_english_word_ratio(text_sample);
    return english_ratio > 0.3f;  // 30% threshold for English words
}


std::string FastLanguageDetector::extract_html_lang(const std::string& html) {
    // Find lang attribute in HTML tag - REGEX-FREE implementation
    size_t html_start = html.find("<html");
    if (html_start == std::string::npos) return "";
    
    size_t html_end = html.find('>', html_start);
    if (html_end == std::string::npos) return "";
    
    std::string html_tag = html.substr(html_start, html_end - html_start);
    
    // Look for lang= attribute
    size_t lang_pos = html_tag.find("lang");
    if (lang_pos == std::string::npos) return "";
    
    // Find the = sign after lang
    size_t eq_pos = html_tag.find('=', lang_pos);
    if (eq_pos == std::string::npos) return "";
    
    // Skip whitespace after =
    size_t start = eq_pos + 1;
    while (start < html_tag.length() && std::isspace(html_tag[start])) start++;
    
    if (start >= html_tag.length()) return "";
    
    // Extract quoted value
    char quote = html_tag[start];
    if (quote != '"' && quote != '\'') return "";
    
    start++; // Skip opening quote
    size_t end = html_tag.find(quote, start);
    if (end == std::string::npos) return "";
    
    std::string lang = html_tag.substr(start, end - start);
    
    // Convert to lowercase
    std::transform(lang.begin(), lang.end(), lang.begin(), ::tolower);
    return lang;
}

bool FastLanguageDetector::is_english_domain(const std::string& url) {
    // English-speaking country domains
    static const std::unordered_set<std::string> ENGLISH_DOMAINS = {
        ".com", ".org", ".net", ".edu", ".gov", ".uk", ".us", ".ca", ".au", 
        ".nz", ".ie", ".za", ".in", "wikipedia.org", "github.com", 
        "stackoverflow.com", "medium.com", "reddit.com", "youtube.com",
        "google.com", "microsoft.com", "apple.com", "amazon.com", "facebook.com",
        "twitter.com", "linkedin.com", "instagram.com", "pinterest.com",
        "geeksforgeeks.org", "w3schools.com", "mozilla.org", "stackoverflow.com"
    };
    
    std::string lower_url = url;
    std::transform(lower_url.begin(), lower_url.end(), lower_url.begin(), ::tolower);
    
    for (const auto& domain : ENGLISH_DOMAINS) {
        if (lower_url.find(domain) != std::string::npos) {
            return true;
        }
    }
    
    return false;
}

float FastLanguageDetector::calculate_english_word_ratio(const std::string& text, int max_words) {
    std::istringstream iss(text);
    std::string word;
    int total_words = 0;
    int english_words = 0;
    
    while (iss >> word && total_words < max_words) {
        // Clean word (remove punctuation)
        std::string clean_word;
        for (char c : word) {
            if (std::isalpha(c)) {
                clean_word += std::tolower(c);
            }
        }
        
        if (clean_word.length() >= 2) {  // Skip very short words
            total_words++;
            
            // Check if it's a common English word
            if (COMMON_ENGLISH_WORDS.find(clean_word) != COMMON_ENGLISH_WORDS.end()) {
                english_words++;
            }
        }
    }
    
    return total_words > 0 ? static_cast<float>(english_words) / total_words : 0.0f;
}

bool FastLanguageDetector::has_non_english_script(const std::string& html) {
    // Check only first 2KB for performance
    size_t check_length = std::min(html.length(), static_cast<size_t>(2048));
    const char* data = html.data();
    size_t i = 0;

    while (i < check_length) {
        unsigned char c = static_cast<unsigned char>(data[i]);
        
        // Skip ASCII characters (0x00-0x7F)
        if (c <= 0x7F) {
            i++;
            continue;
        }

        uint32_t code_point = 0;
        int bytes_consumed = 0;

        // 2-byte UTF-8 sequence (110xxxxx)
        if ((c & 0xE0) == 0xC0) {
            if (i + 1 >= check_length) break;
            bytes_consumed = 2;
            code_point = ((c & 0x1F) << 6) | (data[i+1] & 0x3F);
        }
        // 3-byte UTF-8 sequence (1110xxxx)
        else if ((c & 0xF0) == 0xE0) {
            if (i + 2 >= check_length) break;
            bytes_consumed = 3;
            code_point = ((c & 0x0F) << 12) 
                       | ((data[i+1] & 0x3F) << 6) 
                       | (data[i+2] & 0x3F);
        }
        // 4-byte UTF-8 sequence (11110xxx)
        else if ((c & 0xF8) == 0xF0) {
            if (i + 3 >= check_length) break;
            bytes_consumed = 4;
            code_point = ((c & 0x07) << 18) 
                       | ((data[i+1] & 0x3F) << 12) 
                       | ((data[i+2] & 0x3F) << 6) 
                       | (data[i+3] & 0x3F);
        }
        // Invalid UTF-8, skip 1 byte
        else {
            i++;
            continue;
        }

        // Check against non-English code point ranges
        for (const auto& range : NON_ENGLISH_RANGES) {
            if (code_point >= range.first && code_point <= range.second) {
                return true;
            }
        }

        i += bytes_consumed;
    }
    
    return false;
}

std::string FastLanguageDetector::extract_text_sample(const std::string& html) {
    std::string text;
    text.reserve(1000);  // Reserve space for efficiency
    
    bool in_tag = false;
    bool in_script = false;
    bool in_style = false;
    size_t i = 0;
    
    while (i < html.length() && text.length() < 1000) {
        char c = html[i];
        
        if (c == '<') {
            in_tag = true;
            
            // Check for script/style tags
            if (i + 6 < html.length() && 
                html.substr(i, 7) == "<script") {
                in_script = true;
            } else if (i + 5 < html.length() && 
                       html.substr(i, 6) == "<style") {
                in_style = true;
            }
        } else if (c == '>') {
            in_tag = false;
            
            // Check for closing script/style tags
            if (in_script && i >= 8 && 
                html.substr(i - 8, 9) == "</script>") {
                in_script = false;
            } else if (in_style && i >= 7 && 
                       html.substr(i - 7, 8) == "</style>") {
                in_style = false;
            }
        } else if (!in_tag && !in_script && !in_style) {
            // Add character to text sample
            if (std::isalnum(c) || std::isspace(c)) {
                text += c;
            } else {
                text += ' ';  // Replace punctuation with space
            }
        }
        
        i++;
    }
    
    return text;
}
