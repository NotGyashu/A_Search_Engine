#include "work_stealing_queue.h"

WorkStealingQueue::WorkStealingQueue(size_t num_workers) : num_workers_(num_workers) {
    worker_queues_.resize(num_workers);
    for (size_t i = 0; i < num_workers; ++i) {
        worker_queues_[i] = std::make_unique<WorkerQueue>();
    }
}

bool WorkStealingQueue::push_local(size_t worker_id, const UrlInfo& url) {
    if (worker_id >= num_workers_) return false;
    
    auto& queue = worker_queues_[worker_id];
    std::lock_guard<std::mutex> lock(queue->mutex);
    
    queue->local_queue.push_back(url);
    queue->size.fetch_add(1);
    return true;
}

bool WorkStealingQueue::pop_local(size_t worker_id, UrlInfo& url) {
    if (worker_id >= num_workers_) return false;
    
    auto& queue = worker_queues_[worker_id];
    std::lock_guard<std::mutex> lock(queue->mutex);
    
    if (queue->local_queue.empty()) {
        return false;
    }
    
    url = std::move(queue->local_queue.back());
    queue->local_queue.pop_back();
    queue->size.fetch_sub(1);
    return true;
}

bool WorkStealingQueue::try_steal(size_t worker_id, UrlInfo& url) {
    if (worker_id >= num_workers_) return false;
    
    // Try to steal from other workers
    size_t steal_target = steal_counter_.fetch_add(1) % num_workers_;
    
    for (size_t i = 0; i < num_workers_; ++i) {
        size_t target = (steal_target + i) % num_workers_;
        if (target == worker_id) continue;  // Don't steal from self
        
        auto& queue = worker_queues_[target];
        std::lock_guard<std::mutex> lock(queue->mutex);
        
        if (!queue->local_queue.empty()) {
            url = std::move(queue->local_queue.front());
            queue->local_queue.pop_front();
            queue->size.fetch_sub(1);
            return true;
        }
    }
    
    return false;
}

size_t WorkStealingQueue::total_size() const {
    size_t total = 0;
    for (const auto& queue : worker_queues_) {
        total += queue->size.load();
    }
    return total;
}

bool WorkStealingQueue::empty() const {
    return total_size() == 0;
}
