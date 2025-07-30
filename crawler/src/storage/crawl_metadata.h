#pragma once

#include <string>
#include <chrono>
#include <unordered_map>
#include <mutex>
#include <memory>
#include <vector>
#include <algorithm>
#include <array>
#include "rocksdb/db.h"
#include <stdexcept>
#include <sstream>
#include "concurrentqueue.h"
#include <thread>
#include <atomic>


namespace CrawlScheduling {

// FIX: The complete and correct UrlMetadata struct definition must be here.
struct UrlMetadata {
    std::chrono::system_clock::time_point last_crawl_time;
    std::chrono::system_clock::time_point previous_change_time;
    std::chrono::system_clock::time_point expected_next_crawl;
    std::string content_hash;
    int backoff_multiplier = 1;
    int crawl_count = 0;
    float change_frequency = 0.0f;
    int temporary_failures = 0;
    
    UrlMetadata() {
        auto now = std::chrono::system_clock::now();
        last_crawl_time = now;
        previous_change_time = now;
        expected_next_crawl = now;
    }
    
    void update_next_crawl_time() {
        auto now = std::chrono::system_clock::now();
        auto delta = std::chrono::duration_cast<std::chrono::hours>(now - previous_change_time);
        int backoff_hours = std::min(24 * 30, std::max(1, static_cast<int>(delta.count()) * backoff_multiplier));
        int backoff_minutes = std::max(15, backoff_hours * 60);
        expected_next_crawl = now + std::chrono::minutes(backoff_minutes);
    }
    
    void reset_backoff_on_change() {
        backoff_multiplier = 1;
        previous_change_time = std::chrono::system_clock::now();
        update_next_crawl_time();
    }

    void increase_backoff() {
        backoff_multiplier = std::min(8, backoff_multiplier * 2);
        update_next_crawl_time();
    }
    
    bool is_ready_for_crawl() const {
        return std::chrono::system_clock::now() >= expected_next_crawl;
    }
    
    float calculate_priority() const {
        auto now = std::chrono::system_clock::now();
        if (now >= expected_next_crawl) {
            auto overdue_minutes = std::chrono::duration_cast<std::chrono::minutes>(now - expected_next_crawl).count();
            return 1.0f + (overdue_minutes / 60.0f);
        }
        auto minutes_until_due = std::chrono::duration_cast<std::chrono::minutes>(expected_next_crawl - now).count();
        return std::max(0.1f, 1.0f - (minutes_until_due / (24.0f * 60.0f)));
    }
};

class CrawlMetadataStore {
private:
    // FIX: The full definition of MetadataShard must be here, before it is used.
    struct MetadataShard {
        std::unordered_map<std::string, std::unique_ptr<UrlMetadata>> metadata_map_;
        mutable std::mutex mutex_;
    };

    static constexpr size_t NUM_METADATA_SHARDS = 256;
    std::array<MetadataShard, NUM_METADATA_SHARDS> shards_;
    std::unique_ptr<rocksdb::DB> db_;

    moodycamel::ConcurrentQueue<std::pair<std::string, UrlMetadata>> persistence_queue_;
    std::thread writer_thread_;
    std::atomic<bool> shutdown_{false};

    void persistence_worker();
    std::string serialize(const UrlMetadata& metadata) const;
    UrlMetadata deserialize(const std::string& value) const;
    MetadataShard& get_shard(const std::string& url) const;

public:
    explicit CrawlMetadataStore(const std::string& db_path);
    ~CrawlMetadataStore();

    UrlMetadata* get_or_create_metadata(const std::string& url);
    void update_after_crawl(const std::string& url, const std::string& new_content_hash);
    void record_temporary_failure(const std::string& url);
    size_t size() const;
    size_t count_ready_urls() const;
};

} // namespace CrawlScheduling