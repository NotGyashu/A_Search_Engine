#pragma once

#include <vector>
#include <memory>
#include <deque>
#include <mutex>
#include <atomic>
#include "url_info.h"

/**
 * Lock-free Work Stealing Queue
 */
class WorkStealingQueue {
private:
    struct WorkerQueue {
        std::deque<UrlInfo> local_queue;
        std::mutex mutex;
        std::atomic<size_t> size{0};
    };
    
    std::vector<std::unique_ptr<WorkerQueue>> worker_queues_;
    std::atomic<size_t> steal_counter_{0};
    const size_t num_workers_;

public:
    explicit WorkStealingQueue(size_t num_workers);
    ~WorkStealingQueue() = default;
    
    bool push_local(size_t worker_id, const UrlInfo& url);
    bool pop_local(size_t worker_id, UrlInfo& url);
    bool try_steal(size_t worker_id, UrlInfo& url);
    size_t total_size() const;
    bool empty() const;
};
