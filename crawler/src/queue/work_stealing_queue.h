#pragma once

#include <vector>
#include <memory>
#include <deque>
#include <mutex>
#include <atomic>
#include "url_info.h"
#include "constants.h"

/**
 * Lock-free Work Stealing Queue with Size Limits
 */
class WorkStealingQueue {
private:
    struct WorkerQueue {
        std::deque<UrlInfo> local_queue;
        std::mutex mutex;
        std::atomic<size_t> size{0};
        size_t max_size = CrawlerConstants::Queue::MAX_WORK_STEALING_QUEUE_SIZE; // Max URLs per worker queue
    };
    
    std::vector<std::unique_ptr<WorkerQueue>> worker_queues_;
    std::atomic<size_t> steal_counter_{0};
    const size_t num_workers_;
    const size_t max_per_worker_; 
    const size_t max_total_size_;

public:
    explicit WorkStealingQueue(size_t num_workers, size_t max_per_worker = CrawlerConstants::Queue::MAX_WORK_STEALING_QUEUE_SIZE);
    ~WorkStealingQueue() = default;
    
    bool push_local(size_t worker_id, const UrlInfo& url);
    bool pop_local(size_t worker_id, UrlInfo& url);
    bool try_steal(size_t worker_id, UrlInfo& url);
    size_t total_size() const;
    size_t get_max_size() const { return max_total_size_; }
    bool empty() const;
};
