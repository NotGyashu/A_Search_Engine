# Advanced Performance Recommendations

Based on our performance test results, the crawler is currently achieving around 50-60 pages/second, which is a good improvement but still below our target of 300+ pages/second. Here are additional optimizations we can implement to reach the target performance:

## Critical Path Bottlenecks

### 1. Multi-Interface Workers Scaling

Currently running with 4 workers but can likely scale to 12-16 workers to maximize throughput:

```cpp
// In hybrid_speed_crawler.cpp
const int NUM_WORKERS = 4; // Increase to 12-16 based on CPU cores
```

### 2. Rate Limiter Refinement

The current implementation uses lock-free atomics but still has an unnecessary busy-wait:

```cpp
// Optimize to use adaptive backoff instead of constant busy-wait
static inline void nano_pause(int64_t nanoseconds) {
    const int64_t MAX_SPIN_NS = 500'000; // 0.5ms max spin time
    
    if (nanoseconds < MAX_SPIN_NS) {
        // For very short waits, just spin
        auto start = std::chrono::steady_clock::now();
        while ((std::chrono::steady_clock::now() - start).count() < nanoseconds) {
            _mm_pause(); // CPU-friendly busy wait for short delays
        }
    } else {
        // For longer waits, use a proper sleep to release the CPU
        std::this_thread::sleep_for(std::chrono::nanoseconds(nanoseconds));
    }
}
```

### 3. Complete Lock-Free Queue Implementation

Replace the current URL frontier with moodycamel's ConcurrentQueue:

```cpp
#include "concurrentqueue/concurrentqueue.h"

class UrlFrontier {
private:
    moodycamel::ConcurrentQueue<UrlInfo> primary_queue_;
    moodycamel::ConcurrentQueue<UrlInfo> high_priority_queue_;
    // ...
};
```

### 4. Curl Multi Interface Tuning

Increase the number of simultaneous transfers per worker:

```cpp
// In hybrid_speed_crawler.cpp
const int MAX_CONCURRENT_TRANSFERS_PER_WORKER = 25; // Increase to 40
```

Enable pipelining and multiplexing globally:

```cpp
// In ConnectionPool::configure_connection
curl_multi_setopt(multi_handle, CURLMOPT_PIPELINING, CURLPIPE_MULTIPLEX);
curl_multi_setopt(multi_handle, CURLMOPT_MAX_HOST_CONNECTIONS, 8);
curl_multi_setopt(multi_handle, CURLMOPT_MAX_TOTAL_CONNECTIONS, 100);
```

### 5. Batch Processing Optimization

Increase batch size for database operations:

```cpp
// In CrawlLogger class
constexpr size_t BATCH_SIZE = 100; // Increase from 50 to 100
```

## Memory Optimization

1. Implement zero-copy string parsing where possible
2. Use std::string_view for string operations
3. Reuse memory buffers for responses

## I/O Optimization

1. Use memory-mapped files for reading/writing large datasets
2. Pre-allocate database records in batches
3. Use Write-Ahead Logging for SQLite operations

## Parallel Processing

1. Shard the URL frontier by domain to reduce contention
2. Add a dedicated thread for DNS resolution
3. Process HTML in parallel with network operations

## Final Recommendations

1. Increase worker threads from 4 to 12-16 based on available CPU cores
2. Implement true lock-free concurrency with moodycamel ConcurrentQueue
3. Optimize CURL multi interface settings for higher concurrency
4. Use memory mapping and zero-copy operations for file I/O
5. Add dedicated threads for DNS resolution and HTML parsing

These optimizations should help achieve the target performance of 300+ pages/second while maintaining politeness and compliance with robots.txt rules.
