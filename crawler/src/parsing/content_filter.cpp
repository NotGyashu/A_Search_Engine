#include "content_filter.h"
#include "config_loader.h"     // For loading JSON configuration
#include "url_normalizer.h"    // For extract_domain
#include "constants.h"         // For crawler constants
#include <vector>
#include <iostream>
#include <fstream>
#include <iterator>

// Define the static member variables. They will be populated by the initialize function.
std::unordered_set<std::string> ContentFilter::excluded_extensions_;
std::unordered_set<std::string> ContentFilter::excluded_patterns_;
std::unordered_set<std::string> ContentFilter::high_priority_domains_;

void ContentFilter::initialize(const std::string& config_dir_path) {
    std::cout << "⚙️  Initializing ContentFilter from configuration files..." << std::endl;

    // Helper lambda to load a JSON array of strings from a file into an unordered_set.
    auto load_set_from_json = [&](const std::string& filename, std::unordered_set<std::string>& target_set) {
        std::string full_path = config_dir_path + "/" + filename;
        std::ifstream file(full_path);

        if (!file.is_open()) {
            std::cerr << "⚠️  Warning: Could not open ContentFilter config file: " << full_path 
                      << ". The filter list for this file will be empty." << std::endl;
            return;
        }

        // Read the entire file into a string.
        std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        file.close();

        // Use the provided ConfigLoader to parse the JSON array.
        std::vector<std::string> loaded_vector = ConfigLoader::JsonParser::parse_string_array(content);
        
        // Populate the target set from the loaded vector.
        target_set.insert(loaded_vector.begin(), loaded_vector.end());
        std::cout << "   ✅ Loaded " << target_set.size() << " entries from " << filename << std::endl;
    };

    // Load each configuration file into its respective set.
    load_set_from_json("excluded_extensions.json", excluded_extensions_);
    load_set_from_json("excluded_patterns.json", excluded_patterns_);
    load_set_from_json("high_priority_domains.json", high_priority_domains_);

    std::cout << "✅ ContentFilter initialization complete." << std::endl;
}

bool ContentFilter::is_crawlable_url(const std::string& url) {
    std::string lower_url = url;
    std::transform(lower_url.begin(), lower_url.end(), lower_url.begin(), ::tolower);
    
    // Check for excluded extensions
    for (const auto& ext : excluded_extensions_) {
        if (lower_url.find(ext) != std::string::npos) {
            return false;
        }
    }
    
    // Check for excluded patterns
    for (const auto& pattern : excluded_patterns_) {
        if (lower_url.find(pattern) != std::string::npos) {
            return false;
        }
    }
    
    // Skip very long URLs (Corrected from original code which had a typo)
    if (url.length() > 500) return false;

    return true;
}

float ContentFilter::calculate_priority(const std::string& url, int depth) {
    std::string domain = UrlNormalizer::extract_domain(url);
    
    // Base priority decreases with depth
    float priority = std::max(CrawlerConstants::Priority::MIN_PRIORITY, 
                             1.0f - (depth * CrawlerConstants::Priority::DEPTH_PENALTY));
    
    // High priority domains
    if (high_priority_domains_.find(domain) != high_priority_domains_.end()) {
        priority *= 1.5f;
    }
    
    // Educational and government domains
    if (domain.find(".edu") != std::string::npos || domain.find(".gov") != std::string::npos) {
        priority *= 1.3f;
    }
    
    // News and reference sites
    if (domain.find("news") != std::string::npos || domain.find("wiki") != std::string::npos) {
        priority *= 1.2f;
    }
    
    // Penalize very long URLs
    if (url.length() > 200) {
        priority *= 0.8f;
    }
    
    return std::min(priority, CrawlerConstants::Priority::MAX_PRIORITY); // Cap at configured max
}

bool ContentFilter::is_high_quality_content(const std::string& html) {
    if (html.length() < CrawlerConstants::ContentFilter::MIN_CONTENT_SIZE) return false; // Too short
    if (html.length() > CrawlerConstants::ContentFilter::MAX_CONTENT_SIZE) return false; // Too large
    
    // Check for basic HTML structure
    if (html.find("<html") == std::string::npos && html.find("<!DOCTYPE") == std::string::npos) {
        return false;
    }
    
    // Should contain some actual content
    size_t text_content = 0;
    bool in_tag = false;
    for (char c : html) {
        if (c == '<') in_tag = true;
        else if (c == '>') in_tag = false;
        else if (!in_tag && std::isalnum(c)) text_content++;
    }
    
    return text_content > CrawlerConstants::ContentFilter::MIN_TEXT_CHARACTERS; // At least configured alphanumeric characters
}
