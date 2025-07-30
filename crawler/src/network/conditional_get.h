#pragma once

#include <string>
#include <chrono>
#include <memory>
#include "rocksdb/db.h"

namespace ConditionalGet {

struct HttpHeaders {
    std::string etag;
    std::string last_modified;
    std::chrono::system_clock::time_point response_time;

    HttpHeaders() : response_time(std::chrono::system_clock::now()) {}

    bool has_cache_info() const {
        return !etag.empty() || !last_modified.empty();
    }
};

class ConditionalGetManager {
private:
    std::unique_ptr<rocksdb::DB> db_;

    std::string serialize_headers(const HttpHeaders& headers) const;
    HttpHeaders deserialize_headers(const std::string& data) const;

public:
    explicit ConditionalGetManager(const std::string& db_path);
    ~ConditionalGetManager();

    void update_cache(const std::string& url, const HttpHeaders& headers);
    HttpHeaders get_cache_info(const std::string& url);
    void clear_cache(const std::string& url);
    void print_cache_stats() const;

    // *** This function was moved here from crawler_main.cpp ***
    static HttpHeaders parse_response_headers(const std::string& headers_text);

    ConditionalGetManager(const ConditionalGetManager&) = delete;
    ConditionalGetManager& operator=(const ConditionalGetManager&) = delete;
};

} // namespace ConditionalGet
