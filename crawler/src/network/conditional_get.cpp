#include "conditional_get.h"
#include <iostream>
#include <sstream>
#include <vector>
#include <memory>
#include <algorithm>
#include <cctype>

namespace ConditionalGet {

ConditionalGetManager::ConditionalGetManager(const std::string& db_path) {
    rocksdb::Options options;
    options.create_if_missing = true;
    options.IncreaseParallelism();
    options.OptimizeLevelStyleCompaction();

    rocksdb::DB* db_ptr;
    rocksdb::Status status = rocksdb::DB::Open(options, db_path, &db_ptr);

    if (!status.ok()) {
        throw std::runtime_error("Could not initialize ConditionalGetManager DB: " + status.ToString());
    }
    db_.reset(db_ptr);
    std::cout << "✅ ConditionalGetManager initialized with RocksDB at: " << db_path << std::endl;
}

ConditionalGetManager::~ConditionalGetManager() {
    std::cout << "✅ ConditionalGetManager RocksDB instance shut down." << std::endl;
}

std::string ConditionalGetManager::serialize_headers(const HttpHeaders& headers) const {
    auto time_t = std::chrono::system_clock::to_time_t(headers.response_time);
    return headers.etag + "|" + headers.last_modified + "|" + std::to_string(time_t);
}

HttpHeaders ConditionalGetManager::deserialize_headers(const std::string& data) const {
    HttpHeaders headers;
    std::stringstream ss(data);
    std::string part;
    std::vector<std::string> parts;
    while (std::getline(ss, part, '|')) {
        parts.push_back(part);
    }
    if (parts.size() >= 3) {
        headers.etag = parts[0];
        headers.last_modified = parts[1];
        try {
            headers.response_time = std::chrono::system_clock::from_time_t(std::stoll(parts[2]));
        } catch (...) { /* ignore */ }
    }
    return headers;
}

void ConditionalGetManager::update_cache(const std::string& url, const HttpHeaders& headers) {
    db_->Put(rocksdb::WriteOptions(), url, serialize_headers(headers));
}

HttpHeaders ConditionalGetManager::get_cache_info(const std::string& url) {
    std::string value;
    rocksdb::Status status = db_->Get(rocksdb::ReadOptions(), url, &value);
    if (status.ok()) {
        return deserialize_headers(value);
    }
    return HttpHeaders();
}

void ConditionalGetManager::clear_cache(const std::string& url) {
    db_->Delete(rocksdb::WriteOptions(), url);
}

void ConditionalGetManager::print_cache_stats() const {
    std::string num_keys;
    db_->GetProperty("rocksdb.estimate-num-keys", &num_keys);
    std::cout << "\n=== Conditional GET Cache Statistics (RocksDB) ===" << std::endl;
    std::cout << "Estimated Cached URLs: " << num_keys << std::endl;
    std::cout << "==================================================\n" << std::endl;
}

// *** Implementation of the static header parsing function moved here. ***
HttpHeaders ConditionalGetManager::parse_response_headers(const std::string& headers_text) {
    HttpHeaders headers;
    std::istringstream stream(headers_text);
    std::string line;
    
    while (std::getline(stream, line)) {
        std::string line_lower = line;
        std::transform(line_lower.begin(), line_lower.end(), line_lower.begin(), ::tolower);
        
        if (line_lower.rfind("etag:", 0) == 0) {
            size_t colon_pos = line.find(':');
            if (colon_pos != std::string::npos) {
                headers.etag = line.substr(colon_pos + 1);
                headers.etag.erase(0, headers.etag.find_first_not_of(" \t\r\n"));
                headers.etag.erase(headers.etag.find_last_not_of(" \t\r\n") + 1);
            }
        } else if (line_lower.rfind("last-modified:", 0) == 0) {
            size_t colon_pos = line.find(':');
            if (colon_pos != std::string::npos) {
                headers.last_modified = line.substr(colon_pos + 1);
                headers.last_modified.erase(0, headers.last_modified.find_first_not_of(" \t\r\n"));
                headers.last_modified.erase(headers.last_modified.find_last_not_of(" \t\r\n") + 1);
            }
        }
    }
    return headers;
}

} // namespace ConditionalGet
