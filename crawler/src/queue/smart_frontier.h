#pragma once

#include "crawl_metadata.h"
#include "content_hash.h"
#include "url_info.h"
#include <queue>
#include <vector>
#include <memory>
#include <mutex>
#include <atomic>
#include <chrono>
#include <unordered_set>

namespace CrawlScheduling {

struct SmartUrlInfo {
    std::string url;
    float priority;
    int depth;
    std::string referring_domain;
    std::chrono::steady_clock::time_point discovered_time;
    std::chrono::system_clock::time_point expected_crawl_time;
    
    SmartUrlInfo(const std::string& u, float p = 0.5f, int d = 0, const std::string& ref = "");
    SmartUrlInfo(const UrlInfo& url_info);
    UrlInfo to_url_info() const;
};

struct SmartUrlPriorityComparator {
    bool operator()(const SmartUrlInfo& a, const SmartUrlInfo& b) const;
};

class SmartUrlFrontier {
private:
    static constexpr size_t NUM_PARTITIONS = 16;
    
    struct Partition {
        std::priority_queue<SmartUrlInfo, std::vector<SmartUrlInfo>, SmartUrlPriorityComparator> queue_;
        std::unordered_set<std::string> seen_urls_;
        mutable std::mutex mutex_;
        std::atomic<size_t> size_{0};
        Partition();
    };
    
    std::array<Partition, NUM_PARTITIONS> partitions_;
    std::atomic<size_t> round_robin_counter_{0};
    std::atomic<size_t> max_queue_size_{100000};
    std::atomic<int> max_depth_{5};
    std::shared_ptr<CrawlMetadataStore> metadata_store_;
    
    size_t get_partition_index(const std::string& url) const;
    
public:
    SmartUrlFrontier(std::shared_ptr<CrawlMetadataStore> metadata_store);
    bool enqueue(const UrlInfo& url_info);
   std::vector<UrlInfo> enqueue_batch(std::vector<UrlInfo> batch);
    bool enqueue_smart(const SmartUrlInfo& smart_url);
    bool dequeue(UrlInfo& url_info);
    std::vector<UrlInfo> get_ready_urls(size_t max_count = 5000);
    void update_url_priority(const std::string& url);
    size_t size() const;
    bool is_seen(const std::string& url);
    
    void set_max_queue_size(size_t size);
    void set_max_depth(int depth);
    
    size_t count_ready_urls() const;
};

} // namespace CrawlScheduling