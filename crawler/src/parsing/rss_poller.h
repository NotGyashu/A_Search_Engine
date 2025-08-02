#pragma once

#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <unordered_map>
#include <memory>
#include <functional>

// Forward declarations
class HttpClient;

/**
 * Phase 2: RSS/Atom Feed Polling System
 * Automatically discovers fresh content from RSS/Atom feeds
 * Now uses unified HttpClient for consistent HTTP handling
 */

namespace FeedPolling {

struct FeedEntry {
    std::string url;
    std::string title;
    std::chrono::system_clock::time_point pub_date;
    std::string description;
    float priority = 0.8f; // High priority for feed items
    
    FeedEntry(const std::string& u = "", const std::string& t = "", 
              const std::chrono::system_clock::time_point& pd = std::chrono::system_clock::now())
        : url(u), title(t), pub_date(pd) {}
};

struct FeedInfo {
    std::string feed_url;
    std::string site_domain;
    std::chrono::system_clock::time_point last_poll_time;
    std::chrono::system_clock::time_point next_poll_time;
    int poll_interval_minutes = 10; // Default 10 minutes
    int consecutive_failures = 0;
    bool enabled = true;
    
    FeedInfo(const std::string& url = "") : feed_url(url) {
        auto now = std::chrono::system_clock::now();
        last_poll_time = now;
        next_poll_time = now;
    }
    
    bool is_ready_for_poll() const {
        return enabled && (std::chrono::system_clock::now() >= next_poll_time);
    }
    
    void update_next_poll_time() {
        // Exponential backoff on failures
        int actual_interval = poll_interval_minutes;
        if (consecutive_failures > 0) {
            actual_interval = std::min(60, poll_interval_minutes * (1 << consecutive_failures)); // Max 1 hour
        }
        
        next_poll_time = std::chrono::system_clock::now() + 
                        std::chrono::minutes(actual_interval);
    }
    
    void record_success() {
        consecutive_failures = 0;
        last_poll_time = std::chrono::system_clock::now();
        update_next_poll_time();
    }
    
    void record_failure() {
        consecutive_failures = std::min(5, consecutive_failures + 1); // Cap at 5
        update_next_poll_time();
    }
};

class RSSAtomPoller {
private:
    std::vector<FeedInfo> feeds_;
    std::mutex feeds_mutex_;
    std::thread poller_thread_;
    std::atomic<bool> shutdown_{false};
    
    // Condition variable for graceful shutdown
    std::condition_variable shutdown_cv_;
    std::mutex shutdown_mutex_;
    std::chrono::seconds poll_interval_{30};
    
    // For forwarding discovered URLs to the crawler
    std::function<void(const std::vector<FeedEntry>&)> url_callback_;
    
    // HTTP client for downloading feeds
    HttpClient* http_client_;
    
    void poller_worker();
    std::vector<FeedEntry> parse_rss_feed(const std::string& feed_content);
    std::vector<FeedEntry> parse_atom_feed(const std::string& feed_content);
    std::string download_feed(const std::string& feed_url);
    bool is_recent_entry(const std::chrono::system_clock::time_point& pub_date, int hours_threshold = 24);

public:
    explicit RSSAtomPoller(std::function<void(const std::vector<FeedEntry>&)> callback, HttpClient* client);
    ~RSSAtomPoller();
    
    // Load feeds from config file
    bool load_feeds_from_file(const std::string& feeds_file_path);
    
    // Load feeds from JSON config
    bool load_feeds_from_json(const std::string& json_file_path);
    
    // Add individual feed
    void add_feed(const std::string& feed_url, int poll_interval_minutes = 10);
    
    // Start polling
    void start_polling();
    
    // Stop polling gracefully
    void stop();
    
    // Get statistics
    size_t get_active_feeds_count() const;
    void print_feed_stats() const;

    // New method to configure polling interval for fresh mode
    void set_poll_interval(int seconds);
};

} // namespace FeedPolling
