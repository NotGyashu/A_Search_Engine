#include "connection_pool.h"
#include <iostream>

// Thread-local cache definitions
thread_local std::vector<CURL*> ConnectionPool::thread_local_cache_;
thread_local size_t ConnectionPool::cache_size_ = 0;

ConnectionPool::ConnectionPool() {
    // Initialize connection pool
    for (size_t i = 0; i < max_connections_; ++i) {
        CURL* curl = create_connection();
        if (curl) {
            connections_.emplace_back(curl, std::chrono::steady_clock::now(), false);
        }
    }
}

ConnectionPool::~ConnectionPool() {
    // Cleanup all connections
    for (auto& conn : connections_) {
        if (conn.handle) {
            curl_easy_cleanup(conn.handle);
        }
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
    if (!curl) return;
    
    // Basic configuration
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 3L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 5L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "MiniSearchEngine/1.0");
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
}

CURL* ConnectionPool::acquire_connection() {
    // Try thread-local cache first
    if (cache_size_ > 0) {
        CURL* curl = thread_local_cache_[--cache_size_];
        return curl;
    }
    
    // Find available connection from pool
    for (auto& conn : connections_) {
        bool expected = false;
        if (conn.in_use.compare_exchange_weak(expected, true)) {
            conn.last_used = std::chrono::steady_clock::now();
            return conn.handle;
        }
    }
    
    // Create new connection if none available
    return create_connection();
}

CURL* ConnectionPool::acquire_for_domain(const std::string& domain) {
    // For now, just use regular acquire
    return acquire_connection();
}

void ConnectionPool::release_connection(CURL* curl) {
    if (!curl) return;
    
    // Try to store in thread-local cache
    if (cache_size_ < MAX_THREAD_CACHE) {
        thread_local_cache_.resize(MAX_THREAD_CACHE);
        thread_local_cache_[cache_size_++] = curl;
        return;
    }
    
    // Return to pool
    for (auto& conn : connections_) {
        if (conn.handle == curl) {
            conn.in_use.store(false);
            return;
        }
    }
    
    // Cleanup if not from pool
    curl_easy_cleanup(curl);
}

void ConnectionPool::cleanup_idle_connections() {
    auto now = std::chrono::steady_clock::now();
    const auto timeout = std::chrono::minutes(5);
    
    // Simple cleanup logic - can be enhanced
}

size_t ConnectionPool::active_connections() const {
    size_t active = 0;
    for (const auto& conn : connections_) {
        if (conn.in_use.load()) {
            active++;
        }
    }
    return active;
}
