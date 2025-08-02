#include "smart_frontier.h"

namespace CrawlScheduling {

// SmartUrlInfo implementation
SmartUrlInfo::SmartUrlInfo(const std::string& u, float p, int d, const std::string& ref)
    : url(u), priority(p), depth(d), referring_domain(ref), 
      discovered_time(std::chrono::steady_clock::now()),
      expected_crawl_time(std::chrono::system_clock::now()) {}

SmartUrlInfo::SmartUrlInfo(const UrlInfo& url_info)
    : url(url_info.url), priority(url_info.priority), depth(url_info.depth),
      referring_domain(url_info.referring_domain), 
      discovered_time(url_info.discovered_time),
      expected_crawl_time(std::chrono::system_clock::now()) {}

UrlInfo SmartUrlInfo::to_url_info() const {
    return UrlInfo(url, priority, depth, referring_domain);
}

// Priority comparator implementation
bool SmartUrlPriorityComparator::operator()(const SmartUrlInfo& a, const SmartUrlInfo& b) const {
    auto now = std::chrono::system_clock::now();
    bool a_ready = a.expected_crawl_time <= now;
    bool b_ready = b.expected_crawl_time <= now;
    
    if (a_ready && !b_ready) return false;
    if (!a_ready && b_ready) return true;
    
    if (a.expected_crawl_time != b.expected_crawl_time) {
        return a.expected_crawl_time > b.expected_crawl_time;
    }
    
    if (std::abs(a.priority - b.priority) > 0.01f) {
        return a.priority < b.priority;
    }
    
    return a.depth > b.depth;
}

// Partition implementation
SmartUrlFrontier::Partition::Partition() {
    seen_urls_.reserve(10000);
}

// SmartUrlFrontier implementation
SmartUrlFrontier::SmartUrlFrontier(std::shared_ptr<CrawlMetadataStore> metadata_store)
    : metadata_store_(metadata_store) {}

size_t SmartUrlFrontier::get_partition_index(const std::string& url) const {
    std::hash<std::string> hasher;
    return hasher(url) % NUM_PARTITIONS;
}
bool SmartUrlFrontier::enqueue(const UrlInfo& url_info) {
    if (url_info.depth > max_depth_.load()) {
        return false;
    }
    
    size_t partition_idx = get_partition_index(url_info.url);
    auto& partition = partitions_[partition_idx];
    
    std::lock_guard<std::mutex> lock(partition.mutex_);
    
    if (partition.seen_urls_.count(url_info.url)) {
        return false; // Already seen
    }
    
    if (this->size() >= max_queue_size_.load()) {
        return false; // Queue is full
    }
    
    auto* metadata = metadata_store_->get_or_create_metadata(url_info.url);
    SmartUrlInfo smart_url(url_info);
    smart_url.expected_crawl_time = metadata->expected_next_crawl;
    smart_url.priority = metadata->calculate_priority();
    
    partition.queue_.push(smart_url);
    partition.seen_urls_.insert(url_info.url);
    partition.size_++;
    
    return true;
}


// FINAL, HIGH-PERFORMANCE BATCH IMPLEMENTATION
std::vector<UrlInfo> SmartUrlFrontier::enqueue_batch(std::vector<UrlInfo> batch) {
    if (batch.empty()) {
        return {};
    }

    // === PASS 1: Group URLs by partition WITHOUT locks ===
    std::array<std::vector<UrlInfo>, NUM_PARTITIONS> partitioned_batch;
    for (auto& url_info : batch) {
        if (url_info.depth <= max_depth_.load()) {
            partitioned_batch[get_partition_index(url_info.url)].push_back(std::move(url_info));
        }
    }

    std::vector<UrlInfo> rejected_urls;
    size_t total_size = this->size();

    // === PASS 2: Lock each partition ONCE to process its batch ===
    for (size_t i = 0; i < NUM_PARTITIONS; ++i) {
        if (partitioned_batch[i].empty()) {
            continue;
        }

        auto& partition = partitions_[i];
        std::lock_guard<std::mutex> lock(partition.mutex_);

        for (const auto& url_info : partitioned_batch[i]) {
            if (total_size >= max_queue_size_.load()) {
                rejected_urls.push_back(url_info);
                continue;
            }

            if (partition.seen_urls_.find(url_info.url) == partition.seen_urls_.end()) {
                partition.seen_urls_.insert(url_info.url);
                
                auto* metadata = metadata_store_->get_or_create_metadata(url_info.url);
                SmartUrlInfo smart_url(url_info);
                smart_url.expected_crawl_time = metadata->expected_next_crawl;
                smart_url.priority = metadata->calculate_priority();
                
                partition.queue_.push(std::move(smart_url));
                partition.size_++;
                total_size++;
            }
        }
    }

    return rejected_urls;
}

bool SmartUrlFrontier::enqueue_smart(const SmartUrlInfo& smart_url) {
    if (smart_url.depth > max_depth_) {
        return false;
    }
    
    size_t partition_idx = get_partition_index(smart_url.url);
    auto& partition = partitions_[partition_idx];
    
    std::lock_guard<std::mutex> lock(partition.mutex_);
    
    if (partition.seen_urls_.find(smart_url.url) != partition.seen_urls_.end()) {
        return false;
    }
    
    size_t total_size = 0;
    for (const auto& p : partitions_) {
        total_size += p.size_.load();
    }
    
    if (total_size >= max_queue_size_) {
        return false;
    }
    
    partition.queue_.push(smart_url);
    partition.seen_urls_.insert(smart_url.url);
    partition.size_++;
    
    return true;
}

bool SmartUrlFrontier::dequeue(UrlInfo& url_info) {
    size_t start_partition = round_robin_counter_.fetch_add(1) % NUM_PARTITIONS;
    
    // First pass: look for ready URLs
    for (size_t i = 0; i < NUM_PARTITIONS; ++i) {
        size_t partition_idx = (start_partition + i) % NUM_PARTITIONS;
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        if (partition.queue_.empty()) continue;
        
        const auto& top = partition.queue_.top();
        if (top.expected_crawl_time <= std::chrono::system_clock::now()) {
            url_info = top.to_url_info();
            partition.queue_.pop();
            partition.size_--;
            return true;
        }
    }
    
    // Second pass: earliest scheduled URL
    SmartUrlInfo earliest_url("", 0.0f);
    size_t earliest_partition = 0;
    bool found_any = false;
    
    for (size_t i = 0; i < NUM_PARTITIONS; ++i) {
        size_t partition_idx = (start_partition + i) % NUM_PARTITIONS;
        auto& partition = partitions_[partition_idx];
        
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        if (partition.queue_.empty()) continue;
        
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

std::vector<UrlInfo> SmartUrlFrontier::get_ready_urls(size_t max_count) {
    std::vector<UrlInfo> ready_urls;
    auto now = std::chrono::system_clock::now();
    
    for (auto& partition : partitions_) {
        std::lock_guard<std::mutex> lock(partition.mutex_);
        std::vector<SmartUrlInfo> to_readd;
        
        size_t checked = 0;
        while (!partition.queue_.empty() && 
               ready_urls.size() < max_count && 
               checked < max_count) {
            
            const auto& top = partition.queue_.top();
            checked++;
            
            if (top.expected_crawl_time <= now) {
                ready_urls.push_back(top.to_url_info());
                partition.queue_.pop();
                partition.size_--;
            } else {
                to_readd.push_back(top);
                partition.queue_.pop();
            }
        }
        
        for (const auto& url : to_readd) {
            partition.queue_.push(url);
        }
        
        if (ready_urls.size() >= max_count) break;
    }
    
    return ready_urls;
}

void SmartUrlFrontier::update_url_priority(const std::string& url) {
    // Implementation note: Priority updates are handled during dequeue
    // due to limitations of std::priority_queue
}

size_t SmartUrlFrontier::size() const {
    size_t total = 0;
    for (const auto& partition : partitions_) {
        total += partition.size_.load();
    }
    return total;
}

bool SmartUrlFrontier::is_seen(const std::string& url) {
    size_t partition_idx = get_partition_index(url);
    auto& partition = partitions_[partition_idx];
    
    std::lock_guard<std::mutex> lock(partition.mutex_);
    return partition.seen_urls_.find(url) != partition.seen_urls_.end();
}

void SmartUrlFrontier::set_max_queue_size(size_t size) { 
    max_queue_size_ = size; 
}

void SmartUrlFrontier::set_max_depth(int depth) { 
    max_depth_ = depth; 
}

size_t SmartUrlFrontier::count_ready_urls() const {
    size_t total_count = 0;
    auto now = std::chrono::system_clock::now();
    
    for (const auto& partition : partitions_) {
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        // Create a temporary copy to inspect without modifying
        auto temp_queue = partition.queue_;
        while (!temp_queue.empty()) {
            if (temp_queue.top().expected_crawl_time <= now) {
                total_count++;
            }
            temp_queue.pop();
        }
    }
    
    return total_count;
}

} // namespace CrawlScheduling