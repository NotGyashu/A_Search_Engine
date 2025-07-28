#pragma once

#include <string>
#include <chrono>
#include <unordered_map>
#include <mutex>
#include <memory>
#include <vector>
#include <algorithm>

/**
 * Phase 1: Smart Crawl Scheduling
 * Metadata structures for tracking URL freshness and scheduling
 */

namespace CrawlScheduling {

// Metadata for each URL to track freshness and scheduling
struct UrlMetadata {
    std::chrono::system_clock::time_point last_crawl_time;
    std::chrono::system_clock::time_point previous_change_time;
    std::chrono::system_clock::time_point expected_next_crawl;
    std::string content_hash;
    int backoff_multiplier = 1;
    int crawl_count = 0;
    float change_frequency = 0.0f; // Changes per day
    
    UrlMetadata() {
        auto now = std::chrono::system_clock::now();
        last_crawl_time = now;
        previous_change_time = now;
        expected_next_crawl = now;
    }
    
    // Calculate next crawl time using exponential backoff
    void update_next_crawl_time() {
        auto now = std::chrono::system_clock::now();
        
        // Calculate delta since previous change
        auto delta = std::chrono::duration_cast<std::chrono::hours>(
            now - previous_change_time);
        
        // Exponential backoff: min 15 minutes, max 30 days
        int backoff_hours = std::min(24 * 30, // 30 days max
                                   std::max(1, // 1 hour min (we'll convert to 15 min later)
                                          static_cast<int>(delta.count()) * backoff_multiplier));
        
        // Clamp to configured range: 15 minutes to 30 days
        backoff_hours = std::max(1, backoff_hours); // At least 1 hour for calculation
        
        // Convert to minutes and apply the 15-minute minimum
        int backoff_minutes = std::max(15, backoff_hours * 60);
        if (backoff_minutes > 24 * 60 * 30) { // 30 days in minutes
            backoff_minutes = 24 * 60 * 30;
        }
        
        expected_next_crawl = now + std::chrono::minutes(backoff_minutes);
    }
    
    // Reset backoff when content changes
    void reset_backoff_on_change() {
        backoff_multiplier = 1;
        previous_change_time = std::chrono::system_clock::now();
        update_next_crawl_time();
    }
    
    // Increase backoff when no change detected
    void increase_backoff() {
        backoff_multiplier = std::min(8, backoff_multiplier * 2); // Cap at 8x
        update_next_crawl_time();
    }
    
    // Check if URL is ready for crawling
    bool is_ready_for_crawl() const {
        return std::chrono::system_clock::now() >= expected_next_crawl;
    }
    
    // Calculate priority based on expected crawl time
    float calculate_priority() const {
        auto now = std::chrono::system_clock::now();
        
        // Higher priority for overdue URLs
        if (now >= expected_next_crawl) {
            auto overdue_minutes = std::chrono::duration_cast<std::chrono::minutes>(
                now - expected_next_crawl).count();
            return 1.0f + (overdue_minutes / 60.0f); // Base + hours overdue
        }
        
        // Lower priority for future URLs
        auto minutes_until_due = std::chrono::duration_cast<std::chrono::minutes>(
            expected_next_crawl - now).count();
        return std::max(0.1f, 1.0f - (minutes_until_due / (24.0f * 60.0f))); // Decreases over day
    }
};

// Thread-safe metadata store
class CrawlMetadataStore {
private:
    std::unordered_map<std::string, std::unique_ptr<UrlMetadata>> metadata_map_;
    mutable std::mutex metadata_mutex_;
    
public:
    // Get or create metadata for URL
    UrlMetadata* get_or_create_metadata(const std::string& url) {
        std::lock_guard<std::mutex> lock(metadata_mutex_);
        
        auto it = metadata_map_.find(url);
        if (it == metadata_map_.end()) {
            metadata_map_[url] = std::make_unique<UrlMetadata>();
            return metadata_map_[url].get();
        }
        return it->second.get();
    }
    
    // Update metadata after crawling
    void update_after_crawl(const std::string& url, const std::string& new_content_hash) {
        std::lock_guard<std::mutex> lock(metadata_mutex_);
        
        auto it = metadata_map_.find(url);
        if (it == metadata_map_.end()) {
            // Create new metadata
            auto metadata = std::make_unique<UrlMetadata>();
            metadata->content_hash = new_content_hash;
            metadata->last_crawl_time = std::chrono::system_clock::now();
            metadata->crawl_count = 1;
            metadata->update_next_crawl_time();
            metadata_map_[url] = std::move(metadata);
        } else {
            auto& metadata = it->second;
            bool content_changed = (metadata->content_hash != new_content_hash);
            
            metadata->last_crawl_time = std::chrono::system_clock::now();
            metadata->crawl_count++;
            
            if (content_changed) {
                metadata->content_hash = new_content_hash;
                metadata->reset_backoff_on_change();
            } else {
                metadata->increase_backoff();
            }
        }
    }
    
    // Get ready URLs for crawling (sorted by priority)
    std::vector<std::string> get_ready_urls(size_t max_count = 1000) const {
        std::lock_guard<std::mutex> lock(metadata_mutex_);
        
        std::vector<std::pair<std::string, float>> ready_urls;
        
        for (const auto& [url, metadata] : metadata_map_) {
            if (metadata->is_ready_for_crawl()) {
                ready_urls.emplace_back(url, metadata->calculate_priority());
            }
        }
        
        // Sort by priority (highest first)
        std::sort(ready_urls.begin(), ready_urls.end(),
                 [](const auto& a, const auto& b) { return a.second > b.second; });
        
        std::vector<std::string> result;
        size_t count = std::min(max_count, ready_urls.size());
        result.reserve(count);
        
        for (size_t i = 0; i < count; ++i) {
            result.push_back(ready_urls[i].first);
        }
        
        return result;
    }
    
    // Statistics
    size_t size() const {
        std::lock_guard<std::mutex> lock(metadata_mutex_);
        return metadata_map_.size();
    }
    
    size_t count_ready_urls() const {
        std::lock_guard<std::mutex> lock(metadata_mutex_);
        
        size_t count = 0;
        for (const auto& [url, metadata] : metadata_map_) {
            if (metadata->is_ready_for_crawl()) {
                count++;
            }
        }
        return count;
    }
};

} // namespace CrawlScheduling
