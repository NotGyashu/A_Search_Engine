#pragma once

#include "constants.h"
#include "url_normalizer.h"
#include <string>
#include <unordered_set>
#include <algorithm>

/**
 * Content filter for high-quality pages.
 * Rules are loaded dynamically from JSON configuration files.
 */
class ContentFilter {
private:
    // These sets are now populated at runtime from JSON configuration files.
    static std::unordered_set<std::string> excluded_extensions_;
    static std::unordered_set<std::string> excluded_patterns_;
    static std::unordered_set<std::string> high_priority_domains_;

public:
    /**
     * @brief Initializes the ContentFilter by loading rules from JSON files.
     * * This function MUST be called once at crawler startup before any other
     * ContentFilter methods are used. It loads the lists of excluded extensions,
     * excluded URL patterns, and high-priority domains from the config directory.
     * * @param config_dir_path The file path to the configuration directory 
     * (e.g., "../config").
     */
    static void initialize(const std::string& config_dir_path);

    /**
     * @brief Checks if a URL is likely to lead to crawlable content.
     * @param url The URL to check.
     * @return true if the URL is crawlable, false otherwise.
     */
    static bool is_crawlable_url(const std::string& url);

    /**
     * @brief Calculates a priority score for a URL.
     * @param url The URL to score.
     * @param depth The current crawl depth of the URL.
     * @return A float representing the priority score.
     */
    static float calculate_priority(const std::string& url, int depth);

    /**
     * @brief Determines if the fetched HTML content is of high quality.
     * @param html The raw HTML content of the page.
     * @return true if the content is considered high quality, false otherwise.
     */
    static bool is_high_quality_content(const std::string& html);
};
