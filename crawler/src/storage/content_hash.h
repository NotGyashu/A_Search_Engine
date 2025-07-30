#pragma once

#include <string>
#include <functional>

/**
 * Simple and fast content hashing utilities for Phase 1
 */

namespace ContentHashing {

// Fast hash function for content comparison
class FastContentHasher {
public:
    // Simple but effective hash for content change detection
    static std::string hash_content(const std::string& content) {
        if (content.empty()) {
            return "empty";
        }
        
        // Use standard hash function for simplicity
        std::hash<std::string> hasher;
        size_t hash_value = hasher(content);
        
        // Convert to hex string
        return std::to_string(hash_value);
    }
    
    // Hash key content parts for better change detection
    static std::string hash_key_content(const std::string& html) {
        if (html.empty()) {
            return "empty";
        }
        
        // Extract title, first paragraph, and meta description for hashing
        std::string key_content;
        
        // Simple title extraction
        size_t title_start = html.find("<title>");
        if (title_start != std::string::npos) {
            size_t title_end = html.find("</title>", title_start);
            if (title_end != std::string::npos) {
                key_content += html.substr(title_start + 7, title_end - title_start - 7);
            }
        }
        
        // Simple first paragraph extraction (approximation)
        size_t p_start = html.find("<p>");
        if (p_start != std::string::npos) {
            size_t p_end = html.find("</p>", p_start);
            if (p_end != std::string::npos && p_end - p_start < 1000) {
                key_content += html.substr(p_start + 3, p_end - p_start - 3);
            }
        }
        
        // Use full content if no key parts found
        if (key_content.empty()) {
            // Take first 2KB of content for hashing
            key_content = html.substr(0, std::min(static_cast<size_t>(2048), html.length()));
        }
        
        return hash_content(key_content);
    }
};

} // namespace ContentHashing
