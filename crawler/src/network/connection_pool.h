#pragma once

#include <curl/curl.h>
#include <atomic>
#include <string>
#include "concurrentqueue.h"

// High-performance connection pool using a lock-free queue
class ConnectionPool {
private:
    moodycamel::ConcurrentQueue<CURL*> connections_queue_;
    std::atomic<size_t> total_connections_{0};
    const size_t max_connections_;
    
    CURL* create_connection();
    void configure_connection(CURL* curl);

public:
    explicit ConnectionPool(size_t max_connections = 100);
    ~ConnectionPool();
    
    CURL* acquire_connection();
    void release_connection(CURL* curl);
    size_t active_connections() const;
};