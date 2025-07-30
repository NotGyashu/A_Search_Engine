#pragma once

#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <string>
#include <chrono>

/**
 * HTML Processing Pipeline Task
 */
struct HtmlProcessingTask {
    std::string html;
    std::string url;
    std::string domain;
    int depth;
    std::chrono::steady_clock::time_point fetch_time;
    
    HtmlProcessingTask(std::string h, std::string u, std::string d, int dep)
        : html(std::move(h)), url(std::move(u)), domain(std::move(d)), depth(dep)
        , fetch_time(std::chrono::steady_clock::now()) {}
};

/**
 * HTML Processing Queue for pipeline separation
 */
class HtmlProcessingQueue {
private:
    std::queue<HtmlProcessingTask> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> shutdown_{false};
    static constexpr size_t MAX_QUEUE_SIZE = 1000;

public:
    bool enqueue(HtmlProcessingTask&& task);
    bool dequeue(HtmlProcessingTask& task);
    void shutdown();
    size_t size() const;
};
