#pragma once

#include <curl/curl.h>
#include <vector>
#include <chrono>
#include <atomic>
#include <string>

// High-performance connection pool with per-thread caching
class ConnectionPool {
private:
    struct ConnectionInfo {
        CURL* handle;
        std::chrono::steady_clock::time_point last_used;
        std::atomic<bool> in_use{false};
        
        // Custom constructor for atomic member
        ConnectionInfo(CURL* h, std::chrono::steady_clock::time_point t, bool u) 
            : handle(h), last_used(t), in_use(u) {}
        
        // Move constructor
        ConnectionInfo(ConnectionInfo&& other) noexcept
            : handle(other.handle), last_used(other.last_used), in_use(other.in_use.load()) {}
        
        // Move assignment
        ConnectionInfo& operator=(ConnectionInfo&& other) noexcept {
            if (this != &other) {
                handle = other.handle;
                last_used = other.last_used;
                in_use.store(other.in_use.load());
            }
            return *this;
        }
        
        // Delete copy constructor and assignment
        ConnectionInfo(const ConnectionInfo&) = delete;
        ConnectionInfo& operator=(const ConnectionInfo&) = delete;
    };
    
    std::vector<ConnectionInfo> connections_;
    std::atomic<size_t> max_connections_{100};
    std::atomic<size_t> round_robin_counter_{0};
    
    CURL* create_connection();
    void configure_connection(CURL* curl);

public:
    // Per-thread connection cache for zero-contention acquisition
    static thread_local std::vector<CURL*> thread_local_cache_;
    static thread_local size_t cache_size_;
    static constexpr size_t MAX_THREAD_CACHE = 8;
    
    ConnectionPool();
    ~ConnectionPool();
    
    CURL* acquire_connection();
    CURL* acquire_for_domain(const std::string& domain); // New domain-specific connection pooling
    void release_connection(CURL* curl);
    void cleanup_idle_connections();
    size_t active_connections() const;
};
