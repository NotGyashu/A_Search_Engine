#pragma once

#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <unordered_set>
#include <memory>
#include <functional>
#include <iostream>

// Forward declarations
class HttpClient;
class RobotsTxtCache;

/**
 * Phase 2: Sitemap.xml Parser
 * Automatically discovers URLs from sitemap files
 * Now uses unified HttpClient and tinyxml2 for robust parsing
 */

namespace SitemapParsing {

struct SitemapUrl {
    std::string url;
    std::chrono::system_clock::time_point last_modified;
    std::string change_frequency; // always, hourly, daily, weekly, monthly, yearly, never
    float priority = 0.5f; // 0.0 to 1.0
    
    SitemapUrl(const std::string& u = "") : url(u) {
        last_modified = std::chrono::system_clock::now();
    }
    
    // Convert changefreq to crawl priority
    float get_crawl_priority() const {
        if (change_frequency == "always") return 1.0f;
        else if (change_frequency == "hourly") return 0.9f;
        else if (change_frequency == "daily") return 0.8f;
        else if (change_frequency == "weekly") return 0.6f;
        else if (change_frequency == "monthly") return 0.4f;
        else if (change_frequency == "yearly") return 0.2f;
        else if (change_frequency == "never") return 0.1f;
        return priority; // Use explicit priority if no changefreq
    }
};

struct SitemapInfo {
    std::string sitemap_url;
    std::string site_domain;
    std::chrono::steady_clock::time_point last_parse_time;
    std::chrono::steady_clock::time_point next_parse_time;
    int parse_interval_hours = 24; // Parse daily by default
    int consecutive_failures = 0;
    bool enabled = true;
    bool is_index = false; // Is this a sitemap index?
    float priority = 0.5f; // Priority from sitemap XML or robots.txt discovery (0.0 to 1.0)
    
    SitemapInfo(const std::string& url = "", float prio = 0.5f) : sitemap_url(url), priority(prio) {
        // Reject empty URLs
        if (url.empty()) {
            std::cerr << "⚠️  WARNING: Attempted to create SitemapInfo with empty URL" << std::endl;
            enabled = false; // Disable this sitemap
            return;
        }
        
        auto now = std::chrono::steady_clock::now();
        last_parse_time = now;
        next_parse_time = now;
        
        // Extract domain from URL
        extract_domain_from_url();
        
        // Set parse interval based on priority
        update_parse_interval_from_priority();
    }
    
    void extract_domain_from_url() {
        if (sitemap_url.empty()) return;
        
        size_t start = sitemap_url.find("://");
        if (start != std::string::npos) {
            start += 3;
            size_t end = sitemap_url.find('/', start);
            site_domain = sitemap_url.substr(start, end == std::string::npos ? sitemap_url.length() - start : end - start);
        }
    }
    
    void update_parse_interval_from_priority() {
        // High priority (0.8-1.0) -> 12h, Medium (0.5-0.8) -> 24h, Low (0.0-0.5) -> 48h
        if (priority >= 0.8f) {
            parse_interval_hours = 12;
        } else if (priority >= 0.5f) {
            parse_interval_hours = 24;
        } else {
            parse_interval_hours = 48;
        }
    }
    
    bool is_ready_for_parse() const {
        return enabled && (std::chrono::steady_clock::now() >= next_parse_time);
    }
    
    void update_next_parse_time() {
        // Exponential backoff on failures
        int actual_interval = parse_interval_hours;
        if (consecutive_failures > 0) {
            actual_interval = std::min(72, parse_interval_hours * (1 << consecutive_failures)); // Max 3 days
        }
        
        next_parse_time = std::chrono::steady_clock::now() + 
                         std::chrono::hours(actual_interval);
    }
    
    void record_success() {
        consecutive_failures = 0;
        last_parse_time = std::chrono::steady_clock::now();
        update_next_parse_time();
    }
    
    void record_failure() {
        consecutive_failures = std::min(3, consecutive_failures + 1); // Cap at 3
        update_next_parse_time();
    }
};

class SitemapParser {
private:
    std::vector<SitemapInfo> sitemaps_;
    mutable std::mutex sitemaps_mutex_;
    std::thread parser_thread_;
    std::atomic<bool> shutdown_{false};
    
    // Condition variable for graceful shutdown
    std::condition_variable shutdown_cv_;
    std::mutex shutdown_mutex_;
    
    // Track discovered URLs to avoid duplicates
    std::unordered_set<std::string> discovered_urls_;
    mutable std::mutex discovered_mutex_;
    
    // Domains to monitor for sitemap discovery
    std::vector<std::string> monitored_domains_;
    mutable std::mutex domains_mutex_;
    
    // For forwarding discovered URLs to the crawler
    std::function<void(const std::vector<SitemapUrl>&)> url_callback_;
    
    // HTTP client for downloading sitemaps
    HttpClient* http_client_;
    
    // RobotsTxtCache for centralized sitemap discovery
    RobotsTxtCache* robots_cache_;
    
    void parser_worker();
    std::vector<SitemapUrl> parse_sitemap_xml(const std::string& sitemap_content);
    std::vector<std::string> parse_sitemap_index(const std::string& index_content);
    std::string download_sitemap(const std::string& sitemap_url);
    bool is_recently_modified(const std::chrono::system_clock::time_point& last_mod, int hours_threshold = 168); // 1 week
    void refresh_sitemaps_from_robots_cache();
    
    // Recovery mechanism for corrupted cache
    bool validate_and_recover_cache();

public:
    explicit SitemapParser(std::function<void(const std::vector<SitemapUrl>&)> callback, HttpClient* client, RobotsTxtCache* robots_cache);
    ~SitemapParser();
    
    // Add domains to monitor for sitemap discovery
    void add_domains_to_monitor(const std::vector<std::string>& domains);
    
    // Start parsing
    void start_parsing();
    
    // Stop parsing gracefully
    void stop();
    
    // Get statistics
    size_t get_active_sitemaps_count() const;
    void print_sitemap_stats() const;
};

} // namespace SitemapParsing
