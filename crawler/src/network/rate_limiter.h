#pragma once

#include "constants.h"
#include <string>
#include <atomic>
#include <array>
#include <chrono>
#include <memory>
#include <immintrin.h>
#include "rocksdb/db.h"
#include "concurrentqueue.h"
#include <thread>

class RateLimiter {
private:
    static constexpr size_t NUM_SHARDS = 256;
    std::array<std::atomic<int64_t>, NUM_SHARDS> domain_timestamps_;
    std::array<std::atomic<int>, NUM_SHARDS> failure_counts_;
    
    std::unique_ptr<rocksdb::DB> db_;
    moodycamel::ConcurrentQueue<std::pair<std::string, int64_t>> persistence_queue_;
    std::thread writer_thread_;
    std::atomic<bool> shutdown_{false};

    void persistence_worker();

    // FIX: The definitions for inline functions are moved into the header.
    static inline uint32_t fasthash(const std::string& domain) {
        uint32_t hash = 0x811c9dc5;
        for (char c : domain) {
            hash ^= c;
            hash *= 0x01000193;
        }
        return hash;
    }
    
    static inline void nano_pause(int64_t nanoseconds) {
        auto start = std::chrono::steady_clock::now();
        while (std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::steady_clock::now() - start).count() < nanoseconds) {
            _mm_pause();
        }
    }

public:
    explicit RateLimiter(const std::string& db_path);
    ~RateLimiter();
    
    void wait_for_domain(const std::string& domain);
    void record_failure(const std::string& domain);
    void record_success(const std::string& domain);
    void throttle_domain(const std::string& domain, int seconds);
    bool can_request_now(const std::string& domain);
    void record_request(const std::string& domain);
};