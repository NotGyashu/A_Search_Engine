#include "work_stealing_queue.h"

WorkStealingQueue::WorkStealingQueue(size_t num_workers, size_t max_per_worker)
    : num_workers_(num_workers),
      max_per_worker_(max_per_worker),
      max_total_size_(num_workers * max_per_worker) {
    worker_queues_.reserve(num_workers_);
    for (size_t i = 0; i < num_workers_; ++i) {
        auto q = std::make_unique<WorkerQueue>();
        q->max_size = max_per_worker_;
        worker_queues_.push_back(std::move(q));
    }
}

bool WorkStealingQueue::push_local(size_t worker_id, const UrlInfo& url) {
    auto& q = *worker_queues_[worker_id];
    std::scoped_lock lk(q.mutex);
    if (q.size.load(std::memory_order_relaxed) >= q.max_size) return false;
    q.local_queue.push_back(url);
    q.size.fetch_add(1, std::memory_order_relaxed);
    return true;
}

bool WorkStealingQueue::pop_local(size_t worker_id, UrlInfo& url) {
    auto& q = *worker_queues_[worker_id];
    std::scoped_lock lk(q.mutex);
    if (q.local_queue.empty()) return false;
    url = std::move(q.local_queue.back());
    q.local_queue.pop_back();
    q.size.fetch_sub(1, std::memory_order_relaxed);
    return true;
}

bool WorkStealingQueue::try_steal(size_t worker_id, UrlInfo& url) {
    size_t victim = (worker_id + steal_counter_.fetch_add(1, std::memory_order_relaxed) + 1) % num_workers_;
    auto& q = *worker_queues_[victim];
    std::scoped_lock lk(q.mutex);
    if (q.local_queue.empty()) return false;
    url = std::move(q.local_queue.front());
    q.local_queue.pop_front();
    q.size.fetch_sub(1, std::memory_order_relaxed);
    return true;
}

size_t WorkStealingQueue::total_size() const {
    size_t sum = 0;
    for (auto& q : worker_queues_) sum += q->size.load(std::memory_order_relaxed);
    return sum;
}

bool WorkStealingQueue::empty() const {
    for (auto& q : worker_queues_) {
        if (q->size.load(std::memory_order_relaxed) != 0) return false;
    }
    return true;
}
