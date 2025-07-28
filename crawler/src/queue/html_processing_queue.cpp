#include "html_processing_queue.h"

bool HtmlProcessingQueue::enqueue(HtmlProcessingTask&& task) {
    std::unique_lock<std::mutex> lock(mutex_);
    
    if (queue_.size() >= MAX_QUEUE_SIZE) {
        return false;  // Queue full
    }
    
    queue_.push(std::move(task));
    cv_.notify_one();
    return true;
}

bool HtmlProcessingQueue::dequeue(HtmlProcessingTask& task) {
    std::unique_lock<std::mutex> lock(mutex_);
    
    cv_.wait(lock, [this] { return !queue_.empty() || shutdown_.load(); });
    
    if (queue_.empty()) {
        return false;  // Shutdown
    }
    
    task = std::move(queue_.front());
    queue_.pop();
    return true;
}

void HtmlProcessingQueue::shutdown() {
    shutdown_.store(true);
    cv_.notify_all();
}

size_t HtmlProcessingQueue::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.size();
}
