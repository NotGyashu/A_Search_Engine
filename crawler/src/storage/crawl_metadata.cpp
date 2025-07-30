#include "crawl_metadata.h"
#include "rocksdb/write_batch.h"
#include <vector>
#include <sstream>
#include <stdexcept>

namespace CrawlScheduling {


CrawlMetadataStore::CrawlMetadataStore(const std::string& db_path) {
    rocksdb::Options options;
    options.create_if_missing = true;
    rocksdb::DB* db_ptr;
    rocksdb::Status status = rocksdb::DB::Open(options, db_path, &db_ptr);
    if (!status.ok()) {
        throw std::runtime_error("Could not open CrawlMetadataStore DB: " + status.ToString());
    }
    db_.reset(db_ptr);
    writer_thread_ = std::thread(&CrawlMetadataStore::persistence_worker, this);
}

CrawlMetadataStore::~CrawlMetadataStore() {
    shutdown_ = true;
    if (writer_thread_.joinable()) {
        writer_thread_.join();
    }
}

void CrawlMetadataStore::persistence_worker() {
    std::vector<std::pair<std::string, UrlMetadata>> batch(100);
    while (!shutdown_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        size_t items_dequeued = persistence_queue_.try_dequeue_bulk(batch.begin(), batch.size());
        if (items_dequeued > 0) {
            rocksdb::WriteBatch write_batch;
            for (size_t i = 0; i < items_dequeued; ++i) {
                write_batch.Put(batch[i].first, serialize(batch[i].second));
            }
            db_->Write(rocksdb::WriteOptions(), &write_batch);
        }
    }
    // Final drain of the queue on shutdown to prevent data loss
    size_t items_dequeued;
    do {
        items_dequeued = persistence_queue_.try_dequeue_bulk(batch.begin(), batch.size());
        if (items_dequeued > 0) {
            rocksdb::WriteBatch final_batch;
            for (size_t i = 0; i < items_dequeued; ++i) {
                final_batch.Put(batch[i].first, serialize(batch[i].second));
            }
            db_->Write(rocksdb::WriteOptions(), &final_batch);
        }
    } while (items_dequeued > 0);
}

void CrawlMetadataStore::update_after_crawl(const std::string& url, const std::string& new_content_hash) {
    UrlMetadata* metadata = get_or_create_metadata(url);
    auto& shard = get_shard(url);
    std::lock_guard<std::mutex> lock(shard.mutex_);

    bool content_changed = (metadata->content_hash != new_content_hash);
    metadata->last_crawl_time = std::chrono::system_clock::now();
    metadata->crawl_count++;
    metadata->temporary_failures = 0; // Reset failure count on success

    if (content_changed) {
        metadata->content_hash = new_content_hash;
        metadata->reset_backoff_on_change();
    } else {
        metadata->increase_backoff();
    }

    // Enqueue a copy for persistence instead of writing directly.
    persistence_queue_.enqueue({url, *metadata});
}

void CrawlMetadataStore::record_temporary_failure(const std::string& url) {
    UrlMetadata* metadata = get_or_create_metadata(url);
    auto& shard = get_shard(url);
    std::lock_guard<std::mutex> lock(shard.mutex_);

    metadata->temporary_failures = std::min(5, metadata->temporary_failures + 1);
    long long backoff_minutes = 2 * (1 << (metadata->temporary_failures - 1));
    metadata->expected_next_crawl = std::chrono::system_clock::now() + std::chrono::minutes(backoff_minutes);

    // Enqueue a copy for persistence.
    persistence_queue_.enqueue({url, *metadata});
}

UrlMetadata* CrawlMetadataStore::get_or_create_metadata(const std::string& url) {
    auto& shard = get_shard(url);
    std::lock_guard<std::mutex> lock(shard.mutex_);
    
    // 1. Check in-memory cache first
    auto it = shard.metadata_map_.find(url);
    if (it != shard.metadata_map_.end()) {
        return it->second.get();
    }

    // 2. Not in memory, check persistent RocksDB store
    std::string value;
    if (db_->Get(rocksdb::ReadOptions(), url, &value).ok()) {
        auto metadata_ptr = std::make_unique<UrlMetadata>(deserialize(value));
        UrlMetadata* raw_ptr = metadata_ptr.get();
        shard.metadata_map_[url] = std::move(metadata_ptr);
        return raw_ptr;
    }

    // 3. Not in memory or on disk, create a brand new entry
    auto new_metadata = std::make_unique<UrlMetadata>();
    UrlMetadata* raw_ptr = new_metadata.get();
    // Enqueue the new entry to be persisted to disk asynchronously
    persistence_queue_.enqueue({url, *new_metadata});
    shard.metadata_map_[url] = std::move(new_metadata);
    return raw_ptr;
}

size_t CrawlMetadataStore::size() const {
    size_t total_size = 0;
    for (const auto& shard : shards_) {
        std::lock_guard<std::mutex> lock(shard.mutex_);
        total_size += shard.metadata_map_.size();
    }
    // Note: This may not exactly match the DB size if the queue is not empty,
    // but it's a very close real-time approximation of the tracked URLs.
    return total_size;
}

size_t CrawlMetadataStore::count_ready_urls() const {
    size_t count = 0;
    auto now = std::chrono::system_clock::now();
    for (const auto& shard : shards_) {
        std::lock_guard<std::mutex> lock(shard.mutex_);
        for (const auto& [url, metadata] : shard.metadata_map_) {
            if (metadata->expected_next_crawl <= now) {
                count++;
            }
        }
    }
    return count;
}

CrawlMetadataStore::MetadataShard& CrawlMetadataStore::get_shard(const std::string& url) const {
    static std::hash<std::string> hasher;
    return const_cast<MetadataShard&>(shards_[hasher(url) % NUM_METADATA_SHARDS]);
}

std::string CrawlMetadataStore::serialize(const UrlMetadata& metadata) const {
    std::stringstream ss;
    ss << std::chrono::system_clock::to_time_t(metadata.last_crawl_time) << "|"
       << std::chrono::system_clock::to_time_t(metadata.previous_change_time) << "|"
       << std::chrono::system_clock::to_time_t(metadata.expected_next_crawl) << "|"
       << metadata.content_hash << "|"
       << metadata.backoff_multiplier << "|"
       << metadata.crawl_count << "|"
       << metadata.change_frequency << "|"
       << metadata.temporary_failures;
    return ss.str();
}

UrlMetadata CrawlMetadataStore::deserialize(const std::string& value) const {
    UrlMetadata metadata;
    std::stringstream ss(value);
    std::string part;
    time_t time_val;

    try {
        std::getline(ss, part, '|'); time_val = std::stoll(part); metadata.last_crawl_time = std::chrono::system_clock::from_time_t(time_val);
        std::getline(ss, part, '|'); time_val = std::stoll(part); metadata.previous_change_time = std::chrono::system_clock::from_time_t(time_val);
        std::getline(ss, part, '|'); time_val = std::stoll(part); metadata.expected_next_crawl = std::chrono::system_clock::from_time_t(time_val);
        std::getline(ss, metadata.content_hash, '|');
        std::getline(ss, part, '|'); metadata.backoff_multiplier = std::stoi(part);
        std::getline(ss, part, '|'); metadata.crawl_count = std::stoi(part);
        std::getline(ss, part, '|'); metadata.change_frequency = std::stof(part);
        std::getline(ss, part, '|'); metadata.temporary_failures = std::stoi(part);
    } catch (...) { /* Return default on parse error */ }
    return metadata;
}

} // namespace CrawlScheduling