#include "rate_limiter.h"
#include "rocksdb/write_batch.h"
#include <chrono>
#include <stdexcept>
#include <string>
#include <vector>
#include <thread>

RateLimiter::RateLimiter(const std::string& db_path) {
    rocksdb::Options options;
    options.create_if_missing = true;
    rocksdb::DB* db_ptr;
    rocksdb::Status status = rocksdb::DB::Open(options, db_path, &db_ptr);
    if (!status.ok()) {
        throw std::runtime_error("Could not open RateLimiter RocksDB: " + status.ToString());
    }
    db_.reset(db_ptr);

    for (auto& ts : domain_timestamps_) ts.store(0, std::memory_order_relaxed);
    for (auto& fc : failure_counts_) fc.store(0, std::memory_order_relaxed);
    
    // Start the background writer thread
    writer_thread_ = std::thread(&RateLimiter::persistence_worker, this);
}

RateLimiter::~RateLimiter() {
    shutdown_ = true;
    if (writer_thread_.joinable()) {
        writer_thread_.join();
    }
}

void RateLimiter::persistence_worker() {
    std::vector<std::pair<std::string, int64_t>> batch(100);
    while (!shutdown_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
        
        size_t items_dequeued = persistence_queue_.try_dequeue_bulk(batch.begin(), batch.size());
        
        if (items_dequeued > 0) {
            rocksdb::WriteBatch write_batch;
            for (size_t i = 0; i < items_dequeued; ++i) {
                write_batch.Put(batch[i].first, std::to_string(batch[i].second));
            }
            db_->Write(rocksdb::WriteOptions(), &write_batch);
        }
    }
    // Final drain of the queue on shutdown
    size_t items_dequeued;
    rocksdb::WriteBatch final_batch;
    do {
        items_dequeued = persistence_queue_.try_dequeue_bulk(batch.begin(), batch.size());
        for (size_t i = 0; i < items_dequeued; ++i) {
            final_batch.Put(batch[i].first, std::to_string(batch[i].second));
        }
    } while (items_dequeued > 0);
    db_->Write(rocksdb::WriteOptions(), &final_batch);
}

void RateLimiter::wait_for_domain(const std::string& domain) {
    uint32_t shard = fasthash(domain) % NUM_SHARDS;
    std::string shard_key = std::to_string(shard);
    int64_t last = domain_timestamps_[shard].load(std::memory_order_relaxed);

    if (last == 0 && db_) {
        std::string value;
        if (db_->Get(rocksdb::ReadOptions(), shard_key, &value).ok()) {
            try {
                last = std::stoll(value);
                domain_timestamps_[shard].store(last, std::memory_order_relaxed);
            } catch (...) {}
        }
    }

    // Use system_clock for timestamps that are meaningful across restarts.
    int64_t now = std::chrono::system_clock::now().time_since_epoch().count();
    
    int failures = failure_counts_[shard].load(std::memory_order_relaxed);
    int64_t delay_ns = (CrawlerConstants::RateLimit::BASE_BACKOFF_MS + 
                       std::min(failures * CrawlerConstants::RateLimit::BACKOFF_MULTIPLIER, 
                               CrawlerConstants::RateLimit::MAX_BACKOFF_MS)) * CrawlerConstants::RateLimit::NANOSECONDS_PER_MILLISECOND;
    
    int64_t required_gap = now - last;
    if (required_gap < delay_ns) {
        std::this_thread::sleep_for(std::chrono::nanoseconds(delay_ns - required_gap));
        now = std::chrono::system_clock::now().time_since_epoch().count();
    }
    
    domain_timestamps_[shard].store(now, std::memory_order_relaxed);

    persistence_queue_.enqueue({shard_key, now});
}

void RateLimiter::record_failure(const std::string& domain) {
    uint32_t shard = fasthash(domain) % NUM_SHARDS;
    failure_counts_[shard].fetch_add(1, std::memory_order_relaxed);
}

void RateLimiter::record_success(const std::string& domain) {
    uint32_t shard = fasthash(domain) % NUM_SHARDS;
    failure_counts_[shard].store(0, std::memory_order_relaxed);
}

void RateLimiter::throttle_domain(const std::string& domain, int seconds) {
    uint32_t shard = fasthash(domain) % NUM_SHARDS;
    int64_t throttle_until = std::chrono::system_clock::now().time_since_epoch().count() + (seconds * 1'000'000'000LL);
    
    domain_timestamps_[shard].store(throttle_until, std::memory_order_relaxed);
    persistence_queue_.enqueue({std::to_string(shard), throttle_until});
}

bool RateLimiter::can_request_now(const std::string& domain) {
    uint32_t shard = fasthash(domain) % NUM_SHARDS;
    int64_t now = std::chrono::system_clock::now().time_since_epoch().count();
    int64_t last = domain_timestamps_[shard].load(std::memory_order_relaxed);
    
    // Lazy load if needed for a quick check
    if (last == 0 && db_) {
        std::string value;
        if (db_->Get(rocksdb::ReadOptions(), std::to_string(shard), &value).ok()) {
            try {
                last = std::stoll(value);
                domain_timestamps_[shard].store(last, std::memory_order_relaxed);
            } catch (...) {}
        }
    }
    
    return (now - last) > 50'000'000; // 50ms in nanoseconds
}

void RateLimiter::record_request(const std::string& domain) {
    uint32_t shard = fasthash(domain) % NUM_SHARDS;
    int64_t now = std::chrono::system_clock::now().time_since_epoch().count();
     domain_timestamps_[shard].store(now, std::memory_order_relaxed);
    persistence_queue_.enqueue({std::to_string(shard), now});
}