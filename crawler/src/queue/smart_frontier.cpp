#include "smart_frontier.h"

// Time conversion utilities for system_clock <-> steady_clock
// This allows us to use steady_clock for scheduling while keeping system_clock for persistence
class TimeConverter {
private:
    static const std::chrono::system_clock::time_point system_base;
    static const std::chrono::steady_clock::time_point steady_base;
    
public:
    static std::chrono::steady_clock::time_point to_steady(const std::chrono::system_clock::time_point& sys_time) {
        auto duration_since_base = sys_time - system_base;
        return steady_base + duration_since_base;
    }
    
    static std::chrono::system_clock::time_point to_system(const std::chrono::steady_clock::time_point& steady_time) {
        auto duration_since_base = steady_time - steady_base;
        return system_base + duration_since_base;
    }
};

// Initialize static members
const std::chrono::system_clock::time_point TimeConverter::system_base = std::chrono::system_clock::now();
const std::chrono::steady_clock::time_point TimeConverter::steady_base = std::chrono::steady_clock::now();

namespace CrawlScheduling {


// SmartUrlInfo implementation
SmartUrlInfo::SmartUrlInfo(const std::string& u, float p, int d, const std::string& ref)
    : url(u), priority(p), depth(d), referring_domain(ref), 
      discovered_time(std::chrono::steady_clock::now()),
      expected_crawl_time(std::chrono::steady_clock::now()) {}

SmartUrlInfo::SmartUrlInfo(const UrlInfo& url_info)
    : url(url_info.url), priority(url_info.priority), depth(url_info.depth),
      referring_domain(url_info.referring_domain), 
      discovered_time(url_info.discovered_time),
      expected_crawl_time(std::chrono::steady_clock::now()) {}

UrlInfo SmartUrlInfo::to_url_info() const {
    return UrlInfo(url, priority, depth, referring_domain);
}

// Priority comparator implementation
bool SmartUrlPriorityComparator::operator()(const SmartUrlInfo& a, const SmartUrlInfo& b) const {
    auto now = std::chrono::steady_clock::now();
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
    
    // ✅ FIX: For seed URLs (depth 0) or fresh URLs, force immediate crawling
    if (url_info.depth == 0 || metadata->crawl_count == 0) {
        smart_url.expected_crawl_time = std::chrono::steady_clock::now();
        smart_url.priority = 1.0f; // High priority for seed/fresh URLs
    } else {
        smart_url.expected_crawl_time = TimeConverter::to_steady(metadata->expected_next_crawl);
        smart_url.priority = metadata->calculate_priority();
    }
    
    partition.queue_.push(smart_url);
    partition.seen_urls_.insert(url_info.url);
    partition.size_++;
    
    // Mark partition as ready if this URL is ready to crawl now
    if (smart_url.expected_crawl_time <= std::chrono::steady_clock::now()) {
        mark_partition_ready(partition_idx);
    }
    
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
        
        bool had_ready_urls = false;
        auto now = std::chrono::steady_clock::now();

        for (const auto& url_info : partitioned_batch[i]) {
            if (total_size >= max_queue_size_.load()) {
                rejected_urls.push_back(url_info);
                continue;
            }

            if (partition.seen_urls_.find(url_info.url) == partition.seen_urls_.end()) {
                partition.seen_urls_.insert(url_info.url);
                
                auto* metadata = metadata_store_->get_or_create_metadata(url_info.url);
                SmartUrlInfo smart_url(url_info);
                
                // ✅ FIX: For seed URLs (depth 0) or fresh URLs, force immediate crawling
                if (url_info.depth == 0 || metadata->crawl_count == 0) {
                    smart_url.expected_crawl_time = now;
                    smart_url.priority = 1.0f; // High priority for seed/fresh URLs
                } else {
                    smart_url.expected_crawl_time = TimeConverter::to_steady(metadata->expected_next_crawl);
                    smart_url.priority = metadata->calculate_priority();
                }
                
                partition.queue_.push(std::move(smart_url));
                partition.size_++;
                total_size++;
                
                // Check if this URL is ready to crawl now
                if (smart_url.expected_crawl_time <= now) {
                    had_ready_urls = true;
                }
            }
        }
        
        // If we added ready URLs, mark partition as ready
        if (had_ready_urls) {
            mark_partition_ready(i);
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
    
    // NEW: Update ready partition tracking when enqueueing
    if (smart_url.expected_crawl_time <= std::chrono::steady_clock::now()) {
        mark_partition_ready(partition_idx);
    }
    
    return true;
}

// NEW: High-performance ready partition management methods
void SmartUrlFrontier::mark_partition_ready(size_t partition_idx) {
    auto& partition = partitions_[partition_idx];
    bool was_ready = partition.has_ready_urls_.exchange(true, std::memory_order_relaxed);
    if (!was_ready) {
        ready_partitions_.enqueue(partition_idx);
        ready_partition_count_.fetch_add(1, std::memory_order_relaxed);
    }
}

void SmartUrlFrontier::mark_partition_not_ready(size_t partition_idx) {
    auto& partition = partitions_[partition_idx];
    bool was_ready = partition.has_ready_urls_.exchange(false, std::memory_order_relaxed);
    if (was_ready) {
        ready_partition_count_.fetch_sub(1, std::memory_order_relaxed);
    }
}

bool SmartUrlFrontier::check_and_update_ready_status(size_t partition_idx) {
    auto& partition = partitions_[partition_idx];
    std::lock_guard<std::mutex> lock(partition.mutex_);
    
    if (partition.queue_.empty()) {
        mark_partition_not_ready(partition_idx);
        return false;
    }
    
    bool has_ready = partition.queue_.top().expected_crawl_time <= std::chrono::steady_clock::now();
    if (has_ready) {
        mark_partition_ready(partition_idx);
    } else {
        mark_partition_not_ready(partition_idx);
    }
    return has_ready;
}

bool SmartUrlFrontier::dequeue(UrlInfo& url_info) {
    // NEW: Ultra-fast ready partition check (O(1) instead of O(N))
    size_t ready_partition_idx;
    if (ready_partitions_.try_dequeue(ready_partition_idx)) {
        auto& partition = partitions_[ready_partition_idx];
        std::lock_guard<std::mutex> lock(partition.mutex_);
        
        if (!partition.queue_.empty()) {
            const auto& top = partition.queue_.top();
            if (top.expected_crawl_time <= std::chrono::steady_clock::now()) {
                url_info = top.to_url_info();
                partition.queue_.pop();
                partition.size_--;
                
                // Check if partition still has ready URLs, re-queue if so
                if (!partition.queue_.empty() && 
                    partition.queue_.top().expected_crawl_time <= std::chrono::steady_clock::now()) {
                    ready_partitions_.enqueue(ready_partition_idx);
                } else {
                    mark_partition_not_ready(ready_partition_idx);
                }
                return true;
            }
        }
        
        // Partition no longer ready, mark as such
        mark_partition_not_ready(ready_partition_idx);
    }
    
    // Fallback: If no ready partitions, do a quick scan to find and register ready partitions
    if (ready_partition_count_.load(std::memory_order_relaxed) == 0) {
        auto now = std::chrono::steady_clock::now();
        size_t start_partition = round_robin_counter_.fetch_add(1) % NUM_PARTITIONS;
        
        for (size_t i = 0; i < NUM_PARTITIONS; ++i) {
            size_t partition_idx = (start_partition + i) % NUM_PARTITIONS;
            auto& partition = partitions_[partition_idx];
            
            // Quick check without lock if partition might have ready URLs
            if (partition.size_.load(std::memory_order_relaxed) == 0) continue;
            
            std::lock_guard<std::mutex> lock(partition.mutex_);
            if (!partition.queue_.empty() && 
                partition.queue_.top().expected_crawl_time <= now) {
                mark_partition_ready(partition_idx);
            }
        }
        
        // Try again after discovery
        if (ready_partitions_.try_dequeue(ready_partition_idx)) {
            auto& partition = partitions_[ready_partition_idx];
            std::lock_guard<std::mutex> lock(partition.mutex_);
            
            if (!partition.queue_.empty() && 
                partition.queue_.top().expected_crawl_time <= std::chrono::steady_clock::now()) {
                url_info = partition.queue_.top().to_url_info();
                partition.queue_.pop();
                partition.size_--;
                
                // Check if partition still has ready URLs
                if (!partition.queue_.empty() && 
                    partition.queue_.top().expected_crawl_time <= std::chrono::steady_clock::now()) {
                    ready_partitions_.enqueue(ready_partition_idx);
                } else {
                    mark_partition_not_ready(ready_partition_idx);
                }
                return true;
            } else {
                mark_partition_not_ready(ready_partition_idx);
            }
        }
    }
    
    return false;
}

std::vector<UrlInfo> SmartUrlFrontier::get_ready_urls(size_t max_count) {
    std::vector<UrlInfo> ready_urls;
    auto now = std::chrono::steady_clock::now();
    
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
    auto now = std::chrono::steady_clock::now();
    
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