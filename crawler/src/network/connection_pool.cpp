#include "connection_pool.h"
#include <iostream>

ConnectionPool::ConnectionPool(size_t max_connections) : max_connections_(max_connections) {
    // Pre-populate the pool with a reasonable number of connections
    size_t initial_size = std::min((size_t)10, max_connections_);
    for (size_t i = 0; i < initial_size; ++i) {
        CURL* curl = create_connection();
        if (curl) {
            connections_queue_.enqueue(curl);
            total_connections_++;
        }
    }
}

ConnectionPool::~ConnectionPool() {
    CURL* curl_handle;
    while (connections_queue_.try_dequeue(curl_handle)) {
        curl_easy_cleanup(curl_handle);
    }
}

CURL* ConnectionPool::create_connection() {
    CURL* curl = curl_easy_init();
    if (curl) {
        configure_connection(curl);
    }
    return curl;
}

void ConnectionPool::configure_connection(CURL* curl) {
    // Basic configuration applied to all handles in the pool
    if (!curl) return;
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 3L);
    // Timeouts and other settings will be applied per-request by the worker
}

CURL* ConnectionPool::acquire_connection() {
    CURL* curl = nullptr;
    // Try to get a connection from the queue first
    if (connections_queue_.try_dequeue(curl)) {
        return curl;
    }
    
    // If the queue is empty, create a new connection if we're under the max limit
    if (total_connections_.load() < max_connections_) {
        total_connections_++;
        return create_connection();
    }
    
    // Pool is empty and we've hit the connection limit
    return nullptr;
}

void ConnectionPool::release_connection(CURL* curl) {
    if (!curl) return;
    curl_easy_reset(curl); // Reset the handle for reuse
    connections_queue_.enqueue(curl);
}

size_t ConnectionPool::active_connections() const {
    return total_connections_.load() - connections_queue_.size_approx();
}