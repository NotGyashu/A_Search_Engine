#pragma once

#include "crawl_metadata.h"
#include "content_hash.h"
#include "url_info.h"
#include <queue>
#include <vector>
#include <memory>
#include <mutex>
#include <algorithm>

/**
 * Phase 1: Smart URL Frontier with scheduling-based priority queue
 * Uses metadata to prioritize URLs based on their expected crawl times
 */

namespace CrawlScheduling {

// Enhanced UrlInfo with metadata support
struct SmartUrlInfo {
    std::string url;
    float priority;
    int depth;
    std::string referring_domain;
    std::chrono::steady_clock::time_point discovered_time;
    std::chrono::system_clock::time_point expected_crawl_time;
    
    SmartUrlInfo(const std::string& u, float p = 0.5f, int d = 0, const std::string& ref = "")
        : url(u), priority(p), depth(d), referring_domain(ref), 
          discovered_time(std::chrono::steady_clock::now()),
          expected_crawl_time(std::chrono::system_clock::now()) {}
    
    // Create from regular UrlInfo
    SmartUrlInfo(const UrlInfo& url_info)
        : url(url_info.url), priority(url_info.priority), depth(url_info.depth),
          referring_domain(url_info.referring_domain), 
          discovered_time(url_info.discovered_time),
          expected_crawl_time(std::chrono::system_clock::now()) {}
    
    // Convert to regular UrlInfo for compatibility
    UrlInfo to_url_info() const {
        return UrlInfo(url, priority, depth, referring_domain);
    }
};

// Priority comparator based on expected crawl time and priority
struct SmartUrlPriorityComparator {
    bool operator()(const SmartUrlInfo& a, const SmartUrlInfo& b) const {
        // First priority: ready for crawl vs not ready
        auto now = std::chrono::system_clock::now();
        bool a_ready = a.expected_crawl_time <= now;
        bool b_ready = b.expected_crawl_time <= now;
        
        if (a_ready && !b_ready) return false; // a has higher priority
        if (!a_ready && b_ready) return true;  // b has higher priority
        
        // Both ready or both not ready - use expected crawl time
        if (a.expected_crawl_time != b.expected_crawl_time) {
            return a.expected_crawl_time > b.expected_crawl_time; // Earlier time = higher priority
        }
        
        // Same expected time - use priority score
        if (std::abs(a.priority - b.priority) > 0.01f) {
            return a.priority < b.priority; // Higher priority first
        }
        
        // Same priority - use depth
        return a.depth > b.depth; // Lower depth first
    }
};

// Smart URL Frontier with metadata-based scheduling
class SmartUrlFrontier {
private:
    static constexpr size_t NUM_PARTITIONS = 16;
    
    struct Partition {
        std::priority_queue<SmartUrlInfo, std::vector<SmartUrlInfo>, SmartUrlPriorityComparator> queue_;
        std::unordered_set<std::string> seen_urls_;
        mutable std::mutex mutex_;
        std::atomic<size_t> size_{0};
        
        Partition() {
            seen_urls_.reserve(10000);
        }
    };
    
    std::array<Partition, NUM_PARTITIONS> partitions_;
    std::atomic<size_t> round_robin_counter_{0};
    std::atomic<size_t> max_queue_size_{100000};
    std::atomic<int> max_depth_{5};
    
    // Reference to metadata store
    std::shared_ptr<CrawlMetadataStore> metadata_store_;
    
    size_t get_partition_index(const std::string& url) const {
        std::hash<std::string> hasher;
        return hasher(url) % NUM_PARTITIONS;
    }
    
public:
    SmartUrlFrontier(std::shared_ptr<CrawlMetadataStore> metadata_store)
        : metadata_store_(metadata_store) {}
    
    // Enqueue URL with smart scheduling
    bool enqueue(const UrlInfo& url_info) {
        if (url_info.depth > max_depth_) {
            return false;
        }
        
        size_t partition_idx = get_partition_index(url_info.url);
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        // Check if already seen
        if (partition.seen_urls_.find(url_info.url) != partition.seen_urls_.end()) {
            return false;
        }
        
        // Check total queue size
        size_t total_size = 0;
        for (const auto& p : partitions_) {
            total_size += p.size_.load();
        }
        
        if (total_size >= max_queue_size_) {
            return false;
        }
        
        // Get metadata for this URL
        auto* metadata = metadata_store_->get_or_create_metadata(url_info.url);
        
        // Create smart URL info with expected crawl time
        SmartUrlInfo smart_url(url_info);
        smart_url.expected_crawl_time = metadata->expected_next_crawl;
        smart_url.priority = metadata->calculate_priority();
        
        // Add to queue and seen set
        partition.queue_.push(smart_url);
        partition.seen_urls_.insert(url_info.url);
        partition.size_++;
        
        return true;
    }
    
    // Enqueue SmartUrlInfo directly
    bool enqueue_smart(const SmartUrlInfo& smart_url) {
        if (smart_url.depth > max_depth_) {
            return false;
        }
        
        size_t partition_idx = get_partition_index(smart_url.url);
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        // Check if already seen
        if (partition.seen_urls_.find(smart_url.url) != partition.seen_urls_.end()) {
            return false;
        }
        
        // Check total queue size
        size_t total_size = 0;
        for (const auto& p : partitions_) {
            total_size += p.size_.load();
        }
        
        if (total_size >= max_queue_size_) {
            return false;
        }
        
        // Add to queue and seen set
        partition.queue_.push(smart_url);
        partition.seen_urls_.insert(smart_url.url);
        partition.size_++;
        
        return true;
    }
    
    // Dequeue URL with smart priority
    bool dequeue(UrlInfo& url_info) {
        // Try partitions in round-robin order, but prioritize ready URLs
        size_t start_partition = round_robin_counter_.fetch_add(1) % NUM_PARTITIONS;
        
        // First pass: look for ready URLs
        for (size_t i = 0; i < NUM_PARTITIONS; ++i) {
            size_t partition_idx = (start_partition + i) % NUM_PARTITIONS;
            auto& partition = partitions_[partition_idx];
            
            std::lock_guard<std::mutex> lock(partition.mutex_);
            
            if (partition.queue_.empty()) {
                continue;
            }
            
            const auto& top = partition.queue_.top();
            
            // Check if this URL is ready for crawling
            if (top.expected_crawl_time <= std::chrono::system_clock::now()) {
                url_info = top.to_url_info();
                partition.queue_.pop();
                partition.size_--;
                return true;
            }
        }
        
        // Second pass: if no ready URLs, take the earliest scheduled one
        SmartUrlInfo earliest_url("", 0.0f);
        size_t earliest_partition = 0;
        bool found_any = false;
        
        for (size_t i = 0; i < NUM_PARTITIONS; ++i) {
            size_t partition_idx = (start_partition + i) % NUM_PARTITIONS;
            auto& partition = partitions_[partition_idx];
            
            std::lock_guard<std::mutex> lock(partition.mutex_);
            
            if (partition.queue_.empty()) {
                continue;
            }
            
            const auto& top = partition.queue_.top();
            
            if (!found_any || top.expected_crawl_time < earliest_url.expected_crawl_time) {
                earliest_url = top;
                earliest_partition = partition_idx;
                found_any = true;
            }
        }
        
        if (found_any) {
            auto& partition = partitions_[earliest_partition];
            std::lock_guard<std::mutex> lock(partition.mutex_);
            
            if (!partition.queue_.empty()) {
                url_info = partition.queue_.top().to_url_info();
                partition.queue_.pop();
                partition.size_--;
                return true;
            }
        }
        
        return false;
    }
    
    // Get URLs that are ready for crawling now
    std::vector<UrlInfo> get_ready_urls(size_t max_count = 100) {
        std::vector<UrlInfo> ready_urls;
        auto now = std::chrono::system_clock::now();
        
        for (auto& partition : partitions_) {
            std::lock_guard<std::mutex> lock(partition.mutex_);
            
            // Create temporary vector to hold URLs to re-add
            std::vector<SmartUrlInfo> to_readd;
            
            // Check up to max_count URLs from this partition
            size_t checked = 0;
            while (!partition.queue_.empty() && ready_urls.size() < max_count && checked < max_count) {
                const auto& top = partition.queue_.top();
                checked++;
                
                if (top.expected_crawl_time <= now) {
                    ready_urls.push_back(top.to_url_info());
                    partition.queue_.pop();
                    partition.size_--;
                } else {
                    // Not ready yet, move to re-add list
                    to_readd.push_back(top);
                    partition.queue_.pop();
                }
            }
            
            // Re-add URLs that weren't ready
            for (const auto& url : to_readd) {
                partition.queue_.push(url);
            }
            
            if (ready_urls.size() >= max_count) {
                break;
            }
        }
        
        return ready_urls;
    }
    
    // Update URL priority based on metadata
    void update_url_priority(const std::string& url) {
        size_t partition_idx = get_partition_index(url);
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        // This is complex with std::priority_queue
        // For now, we'll let the natural dequeue process handle priority updates
        // In a production system, we might use a more sophisticated data structure
    }
    
    // Get total size
    size_t size() const {
        size_t total = 0;
        for (const auto& partition : partitions_) {
            total += partition.size_.load();
        }
        return total;
    }
    
    // Check if URL is seen
    bool is_seen(const std::string& url) {
        size_t partition_idx = get_partition_index(url);
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        return partition.seen_urls_.find(url) != partition.seen_urls_.end();
    }
    
    // Configuration
    void set_max_queue_size(size_t size) { max_queue_size_ = size; }
    void set_max_depth(int depth) { max_depth_ = depth; }
    
    // Statistics
    size_t count_ready_urls() const {
        // Note: Since we can't iterate through std::priority_queue without modifying it,
        // we return the total queue size as an approximation
        size_t total_count = 0;
        
        for (const auto& partition : partitions_) {
            std::lock_guard<std::mutex> lock(partition.mutex_);
            total_count += partition.queue_.size();
        }
        
        return total_count;
    }
};

} // namespace CrawlScheduling
