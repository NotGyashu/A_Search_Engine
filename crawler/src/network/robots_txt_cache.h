#pragma once

#include <string>
#include <chrono>
#include <mutex>
#include <memory>
#include <unordered_map>
#include <vector>
#include "rocksdb/db.h"

// The result of a non-blocking check against robots.txt rules.
enum class RobotsCheckResult {
    ALLOWED,
    DISALLOWED,
    DEFERRED_FETCH_STARTED
};

// Sitemap information structure
struct SitemapInfo {
    std::string url;
    float priority = 0.5f; // 0.0 to 1.0, higher is more important
    int parse_interval_hours = 24; // How often to parse this sitemap
    std::chrono::system_clock::time_point discovered_time;
    
    SitemapInfo(const std::string& u = "", float p = 0.5f) : url(u), priority(p) {
        discovered_time = std::chrono::system_clock::now();
        // Set parse interval based on priority
        if (priority >= 0.8f) {
            parse_interval_hours = 12; // High priority: parse every 12 hours
        } else if (priority >= 0.5f) {
            parse_interval_hours = 24; // Medium priority: parse daily
        } else {
            parse_interval_hours = 48; // Low priority: parse every 2 days
        }
    }
};

class RobotsTxtCache {
private:
    struct RobotsInfo {
        std::string content;
        std::chrono::steady_clock::time_point timestamp;
        bool is_valid = false;
        int last_http_status = 0; // Store the last HTTP status for re-fetch logic
        int crawl_delay = 0; // Crawl-delay in seconds
        std::vector<SitemapInfo> sitemaps; // Discovered sitemaps from this robots.txt
        bool sitemaps_parsed = false; // Whether we've extracted sitemaps from content
    };
    
    mutable std::mutex mutex_;
    // Fast in-memory cache for active crawling
    std::unordered_map<std::string, RobotsInfo> cache_;
    // Persistent disk cache
    std::unique_ptr<rocksdb::DB> db_; 

    // The default refresh interval is now 30 days.
    const std::chrono::hours cache_expiry_{30 * 24};
    
    // Helper methods for serialization to/from RocksDB
    std::string serialize(const RobotsInfo& info) const;
    RobotsInfo deserialize(const std::string& value) const;

    // Helper method for parsing rules
    bool parse_rules(const std::string& content, const std::string& user_agent, 
                     std::vector<std::string>& allowed, std::vector<std::string>& disallowed) const;
                     
    // Helper method for parsing sitemaps from robots.txt content
    std::vector<SitemapInfo> parse_sitemaps_from_robots(const std::string& content) const;

public:
    explicit RobotsTxtCache(const std::string& db_path);
    
    RobotsCheckResult is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent = "*");
    
    // This function is called by the worker *after* a robots.txt is downloaded.
    void update_cache(const std::string& domain, const std::string& content, int http_status);
    
    /**
     * Call this method from the worker if a crawl is blocked by a cached rule
     * that you believe to be outdated. It will remove the entry from the cache,
     * forcing a fresh download on the next request to that domain.
     */
    void invalidate_for_domain(const std::string& domain);
    
    /**
     * Get all discovered sitemaps for a domain.
     * Returns empty vector if domain not in cache or no sitemaps found.
     * Thread-safe.
     */
    std::vector<SitemapInfo> get_sitemaps_for_domain(const std::string& domain);
    
    /**
     * Check if robots.txt exists for a domain (either in memory or disk cache).
     * Thread-safe.
     */
    bool has_robots_for_domain(const std::string& domain) const;
    
    /**
     * Get crawl delay for a domain. Returns 0 if no delay specified or domain not cached.
     * Thread-safe.
     */
    int get_crawl_delay(const std::string& domain) const;
};