# Crawler Speed Optimization Plan: Target 50+ Pages/Second

## Current Performance Analysis

### Current Metrics (from recent run):
- **Current Rate**: ~8.8-10.4 pages/sec
- **Target Rate**: 50+ pages/sec
- **Gap**: 5x improvement needed

### Identified Bottlenecks:

#### 1. Network I/O Bottlenecks (Primary)
- **Current**: 8 threads, 10-second timeout
- **Issues**: 
  - Long timeouts waste time on slow sites
  - Limited connection reuse
  - DNS lookups not cached aggressively
  - No connection pooling per domain

#### 2. Content Processing Bottlenecks
- **Current**: Full HTML parsing for every page
- **Issues**:
  - Gumbo parser runs on every page
  - Text extraction is slow
  - Content quality checking is expensive
  - Link extraction processes entire HTML

#### 3. Storage I/O Bottlenecks
- **Current**: SQLite + JSON + CSV logging
- **Issues**:
  - Multiple write operations per page
  - File I/O blocks worker threads
  - No write batching optimization
  - Synchronous database writes

#### 4. Thread Synchronization Bottlenecks
- **Current**: Heavy lock contention
- **Issues**:
  - Global queue lock
  - Database write locks
  - File write locks
  - Rate limiter locks

## Optimization Strategy

### Phase 1: Network Optimizations (Target: 20-25 pages/sec)

#### 1.1 Aggressive Timeout Reduction
```cpp
curl_easy_setopt(curl, CURLOPT_TIMEOUT, 3L);        // 3 sec total
curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 1L); // 1 sec connect
```

#### 1.2 Connection Pool Per Domain
```cpp
class DomainConnectionPool {
    std::unordered_map<std::string, std::queue<CURL*>> pools_;
    std::mutex pool_mutex_;
    static const size_t MAX_CONNECTIONS_PER_DOMAIN = 3;
};
```

#### 1.3 DNS Caching
```cpp
curl_easy_setopt(curl, CURLOPT_DNS_CACHE_TIMEOUT, 300L); // 5 min cache
```

#### 1.4 HTTP/2 and Keep-Alive Optimization
```cpp
curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2_0);
curl_easy_setopt(curl, CURLOPT_TCP_KEEPALIVE, 1L);
curl_easy_setopt(curl, CURLOPT_TCP_KEEPIDLE, 60L);
```

### Phase 2: Processing Optimizations (Target: 35-40 pages/sec)

#### 2.1 Lazy Content Processing
- Process content only when batch is saved
- Skip quality checks for known good domains
- Cache domain quality scores

#### 2.2 Fast Link Extraction
```cpp
// Replace Gumbo with regex-based extraction for speed
std::regex link_regex(R"(href\s*=\s*["']([^"']+)["'])");
```

#### 2.3 Optimized Content Quality Check
```cpp
bool is_high_quality_fast(const std::string& html) {
    // Quick heuristics instead of full parsing
    if (html.length() < 500 || html.length() > 10*1024*1024) return false;
    
    // Count tags vs text ratio
    size_t tag_count = std::count(html.begin(), html.end(), '<');
    return (html.length() / (tag_count + 1)) > 50; // Avg 50 chars between tags
}
```

### Phase 3: Storage Optimizations (Target: 45-50 pages/sec)

#### 3.1 Asynchronous Storage Pipeline
```cpp
class AsyncStorageManager {
    std::queue<StorageTask> storage_queue_;
    std::thread storage_worker_;
    std::condition_variable cv_;
};
```

#### 3.2 Batch Database Writes
```cpp
// Accumulate 100 records before writing
const size_t DB_BATCH_SIZE = 100;
std::vector<PageMetadata> db_batch_;
```

#### 3.3 Memory-Mapped File I/O
```cpp
// Use memory-mapped files for large batch writes
#include <sys/mman.h>
```

### Phase 4: Advanced Optimizations (Target: 50+ pages/sec)

#### 4.1 Lock-Free Data Structures
```cpp
#include <atomic>
#include <lockfree/queue.hpp>

class LockFreeUrlQueue {
    std::atomic<size_t> size_{0};
    lockfree::queue<UrlInfo> queue_;
};
```

#### 4.2 Thread Pool Architecture
```cpp
class WorkerThreadPool {
    std::vector<std::thread> workers_;
    std::vector<std::queue<UrlInfo>> thread_local_queues_;
    // Work-stealing between threads
};
```

#### 4.3 SIMD Optimizations
```cpp
// Use SIMD for string operations
#include <immintrin.h>
bool fast_string_search(const std::string& haystack, const std::string& needle);
```

## Implementation Plan

### Week 1: Core Optimizations
- [ ] Remove debug statements ✅
- [ ] Implement aggressive timeouts
- [ ] Add per-domain connection pools
- [ ] Optimize DNS caching
- [ ] Target: 20-25 pages/sec

### Week 2: Processing Pipeline
- [ ] Implement lazy content processing
- [ ] Fast regex-based link extraction
- [ ] Optimized quality checks
- [ ] Content processing caching
- [ ] Target: 35-40 pages/sec

### Week 3: Storage Pipeline
- [ ] Asynchronous storage manager
- [ ] Batch database operations
- [ ] Memory-mapped file I/O
- [ ] Storage queue optimization
- [ ] Target: 45-50 pages/sec

### Week 4: Advanced Features
- [ ] Lock-free data structures
- [ ] Thread pool with work stealing
- [ ] SIMD string operations
- [ ] Memory pool allocators
- [ ] Target: 50+ pages/sec

## Configuration for High Speed

### Recommended Settings
```bash
# High-speed configuration
./crawler 32 3 50000

# System optimizations
ulimit -n 65536  # Increase file descriptor limit
echo never > /sys/kernel/mm/transparent_hugepage/enabled
```

### Kernel Tuning
```bash
# Network optimizations
sysctl -w net.core.rmem_max=67108864
sysctl -w net.core.wmem_max=67108864
sysctl -w net.ipv4.tcp_rmem="4096 87380 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 65536 67108864"
```

## Monitoring and Metrics

### Key Performance Indicators
1. **Pages/second**: Primary metric
2. **Queue utilization**: Should stay > 80%
3. **Thread utilization**: Should be > 90%
4. **Network errors**: Should be < 5%
5. **Memory usage**: Should be stable
6. **Storage backlog**: Should be minimal

### Profiling Tools
```bash
# CPU profiling
perf record -g ./crawler
perf report

# Memory profiling
valgrind --tool=massif ./crawler

# Network profiling
netstat -i
iftop
```

## Expected Results

### Performance Progression
- **Phase 1**: 8 → 25 pages/sec (3x improvement)
- **Phase 2**: 25 → 40 pages/sec (1.6x improvement)  
- **Phase 3**: 40 → 50 pages/sec (1.25x improvement)
- **Phase 4**: 50+ pages/sec (target achieved)

### Resource Requirements
- **CPU**: 4-8 cores at 80-90% utilization
- **Memory**: 2-4GB peak usage
- **Network**: 50-100 Mbps sustained
- **Storage**: 100+ MB/s write capability

## Risk Mitigation

### Potential Issues
1. **Rate limiting**: May trigger more aggressive blocking
2. **Memory usage**: Higher concurrency = more memory
3. **Error rates**: Faster crawling may increase errors
4. **Site overload**: Risk of overwhelming target sites

### Mitigation Strategies
1. **Smart rate limiting**: Per-domain adaptive delays
2. **Memory bounds**: Implement strict memory limits
3. **Error handling**: Exponential backoff on errors
4. **Politeness**: Respect robots.txt and server responses

## Success Criteria

### Must-Have
- [ ] Achieve 50+ pages/second sustained rate
- [ ] Maintain < 5% error rate
- [ ] Keep memory usage under 4GB
- [ ] Preserve data quality and completeness

### Nice-to-Have
- [ ] Achieve 75+ pages/second peak rate
- [ ] Support 100+ concurrent domains
- [ ] Real-time processing pipeline
- [ ] Auto-scaling based on system resources
