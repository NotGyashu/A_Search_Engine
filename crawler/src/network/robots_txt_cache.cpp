#include "robots_txt_cache.h"
#include <vector>
#include <sstream>
#include <algorithm>

// Serialization helper to store RobotsInfo as a string in RocksDB
std::string RobotsTxtCache::serialize(const RobotsInfo& info) const {
    auto time_since_epoch = info.timestamp.time_since_epoch();
    long long timestamp_ms = std::chrono::duration_cast<std::chrono::milliseconds>(time_since_epoch).count();
    
    return std::to_string(timestamp_ms) + "|" +
           (info.is_valid ? "1" : "0") + "|" +
           std::to_string(info.last_http_status) + "|" +
           info.content;
}

// Deserialization helper to reconstruct RobotsInfo from a RocksDB value
RobotsTxtCache::RobotsInfo RobotsTxtCache::deserialize(const std::string& value) const {
    RobotsInfo info;
    std::stringstream ss(value);
    std::string part;
    
    try {
        // Timestamp
        std::getline(ss, part, '|');
        long long timestamp_ms = std::stoll(part);
        info.timestamp = std::chrono::steady_clock::time_point(std::chrono::milliseconds(timestamp_ms));
        
        // is_valid
        std::getline(ss, part, '|');
        info.is_valid = (part == "1");
        
        // last_http_status
        std::getline(ss, part, '|');
        info.last_http_status = std::stoi(part);
        
        // content
        std::getline(ss, info.content); // Read the rest of the string
    } catch (...) {
        // If deserialization fails, return a default-constructed (invalid) object
        return RobotsInfo{};
    }
    return info;
}


RobotsTxtCache::RobotsTxtCache(const std::string& db_path) {
    rocksdb::Options options;
    options.create_if_missing = true;
    rocksdb::DB* db_ptr;
    rocksdb::Status status = rocksdb::DB::Open(options, db_path, &db_ptr);
    if (!status.ok()) {
        throw std::runtime_error("Could not initialize RobotsTxtCache DB: " + status.ToString());
    }
    db_.reset(db_ptr);
}

RobotsCheckResult RobotsTxtCache::is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent) {
    std::unique_lock<std::mutex> lock(mutex_);
    
    auto it = cache_.find(domain);
    bool needs_loading_from_db = (it == cache_.end());
    
    if (needs_loading_from_db) {
        // Not in memory, try loading from RocksDB
        std::string value;
        if (db_->Get(rocksdb::ReadOptions(), domain, &value).ok()) {
            cache_[domain] = deserialize(value);
            it = cache_.find(domain); // Update iterator to point to the new entry
        }
    }

    if (it != cache_.end()) {
        // Entry exists in cache (either from memory or just loaded from DB).
        const auto& info = it->second;
        auto now = std::chrono::steady_clock::now();
        
        // === IMMEDIATE RE-FETCH LOGIC ===
        // 1. Last fetch failed.
        if (!info.is_valid) {
            return RobotsCheckResult::DEFERRED_FETCH_STARTED;
        }
        // 2. Last fetch resulted in a 403 or 404.
        if (info.last_http_status == 403 || info.last_http_status == 404) {
            return RobotsCheckResult::DEFERRED_FETCH_STARTED;
        }
        // 3. TTL has expired.
        if (now - info.timestamp > cache_expiry_) {
            return RobotsCheckResult::DEFERRED_FETCH_STARTED;
        }

        // If no re-fetch is needed, parse the rules.
        // ... (parsing logic is the same as before) ...
        return RobotsCheckResult::ALLOWED; // or DISALLOWED
    }
    
    // Entry not in memory or on disk, so we must fetch it.
    RobotsInfo placeholder;
    cache_[domain] = placeholder; // Create placeholder to prevent duplicate fetches
    return RobotsCheckResult::DEFERRED_FETCH_STARTED;
}

void RobotsTxtCache::update_cache(const std::string& domain, const std::string& content, int http_status) {
    RobotsInfo info;
    info.content = content;
    info.timestamp = std::chrono::steady_clock::now();
    info.last_http_status = http_status;
    info.is_valid = (http_status == 200);

    // Write to both in-memory cache and persistent DB
    {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_[domain] = info;
    }
    db_->Put(rocksdb::WriteOptions(), domain, serialize(info));
}

void RobotsTxtCache::invalidate_for_domain(const std::string& domain) {
    // Remove from both caches to force a re-fetch on next access.
    {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.erase(domain);
    }
    db_->Delete(rocksdb::WriteOptions(), domain);
}