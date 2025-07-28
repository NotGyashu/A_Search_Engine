#pragma once

#include "constants.h"
#include <string>
#include <atomic>
#include <array>
#include <chrono>
#include <immintrin.h> // For _mm_pause() intrinsic

// Lock-free rate limiter using atomic operations and sharding
class RateLimiter {
private:
    static constexpr size_t NUM_SHARDS = 256;
    std::array<std::atomic<int64_t>, NUM_SHARDS> domain_timestamps_;
    std::array<std::atomic<int>, NUM_SHARDS> failure_counts_;
    
    // Fast hash function for domain sharding - fixed for 32-bit
    static inline uint32_t fasthash(const std::string& domain) {
        uint32_t hash = 0x811c9dc5; // 32-bit FNV offset basis
        for (char c : domain) {
            hash ^= c;
            hash *= 0x01000193; // 32-bit FNV prime
        }
        return hash;
    }
    
    // CPU-friendly nano sleep
    static inline void nano_pause(int64_t nanoseconds) {
        auto start = std::chrono::steady_clock::now();
        while (std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::steady_clock::now() - start).count() < nanoseconds) {
            _mm_pause(); // x86/x64 intrinsic
        }
    }

public:
    RateLimiter() {
        // Initialize all timestamps to 0
        for (auto& ts : domain_timestamps_) {
            ts.store(0, std::memory_order_relaxed);
        }
        for (auto& fc : failure_counts_) {
            fc.store(0, std::memory_order_relaxed);
        }
    }
    
    void wait_for_domain(const std::string& domain);
    void record_failure(const std::string& domain);
    void record_success(const std::string& domain);
    void set_custom_delay(const std::string& domain, int delay_ms) { /* No-op in lock-free version */ }
    void throttle_domain(const std::string& domain, int seconds);
    bool can_request_now(const std::string& domain);
    void record_request(const std::string& domain);
};
