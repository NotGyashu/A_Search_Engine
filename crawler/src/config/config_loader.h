#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <sstream>

/**
 * Common Configuration Loader
 * Supports loading JSON configuration files with comment support
 */

namespace ConfigLoader {

/**
 * Feed configuration structure
 */
struct FeedConfig {
    std::string url;
    int poll_interval_minutes;
    int priority;
    
    FeedConfig(const std::string& u = "", int interval = 10, int p = 8) 
        : url(u), poll_interval_minutes(interval), priority(p) {}
};

/**
 * Sitemap configuration structure
 */
struct SitemapConfig {
    std::string url;
    int parse_interval_hours;
    int priority;
    
    SitemapConfig(const std::string& u = "", int interval = 24, int p = 8) 
        : url(u), parse_interval_hours(interval), priority(p) {}
};

/**
 * Load seed URLs from JSON file
 */
std::vector<std::string> load_seed_urls(const std::string& config_path);

/**
 * Load RSS feed configurations from JSON file
 */
std::vector<FeedConfig> load_feed_configs(const std::string& config_path);

/**
 * Simple JSON parser for our specific formats
 * Supports comments (lines starting with // or #)
 */
namespace JsonParser {
    std::string remove_comments(const std::string& json_content);
    std::vector<std::string> parse_string_array(const std::string& json_content);
    std::vector<FeedConfig> parse_feed_array(const std::string& json_content);
}

} // namespace ConfigLoader
