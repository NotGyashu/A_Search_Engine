#include "robots_txt_cache.h"
#include <vector>
#include <sstream>
#include <algorithm>
#include <string_view>
#include "tracy/Tracy.hpp"

// Serialization helper to store RobotsInfo as a string in RocksDB
std::string RobotsTxtCache::serialize(const RobotsInfo& info) const {
    auto time_since_epoch = info.timestamp.time_since_epoch();
    long long timestamp_ms = std::chrono::duration_cast<std::chrono::milliseconds>(time_since_epoch).count();
    
    std::ostringstream oss;
    oss << timestamp_ms << "|"
        << (info.is_valid ? "1" : "0") << "|"
        << info.last_http_status << "|"
        << info.crawl_delay << "|"
        << (info.sitemaps_parsed ? "1" : "0") << "|"
        << info.sitemaps.size() << "|";
    
    // Serialize sitemaps
    for (const auto& sitemap : info.sitemaps) {
        auto sitemap_time = sitemap.discovered_time.time_since_epoch();
        long long sitemap_timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(sitemap_time).count();
        oss << sitemap.url << "|" << sitemap.priority << "|" << sitemap.parse_interval_hours << "|" << sitemap_timestamp << "|";
    }
    
    oss << info.content;
    return oss.str();
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
        
        // crawl_delay
        std::getline(ss, part, '|');
        info.crawl_delay = std::stoi(part);
        
        // sitemaps_parsed
        std::getline(ss, part, '|');
        info.sitemaps_parsed = (part == "1");
        
        // sitemap count
        std::getline(ss, part, '|');
        size_t sitemap_count = std::stoull(part);
        
        // Parse sitemaps
        for (size_t i = 0; i < sitemap_count; ++i) {
            SitemapInfo sitemap;
            
            // URL
            std::getline(ss, sitemap.url, '|');
            
            // Priority
            std::getline(ss, part, '|');
            sitemap.priority = std::stof(part);
            
            // Parse interval
            std::getline(ss, part, '|');
            sitemap.parse_interval_hours = std::stoi(part);
            
            // Discovered time
            std::getline(ss, part, '|');
            long long sitemap_timestamp = std::stoll(part);
            sitemap.discovered_time = std::chrono::system_clock::time_point(std::chrono::milliseconds(sitemap_timestamp));
            
            info.sitemaps.push_back(sitemap);
        }
        
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

// In src/network/robots_txt_cache.cpp

RobotsCheckResult RobotsTxtCache::is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent) {
    //
    // === PASS 1: Quick, optimistic check with a short lock ===
    //
    {
        std::unique_lock<std::mutex> lock(mutex_);
        auto it = cache_.find(domain);
        if (it != cache_.end()) {
            // CRITICAL: Copy the info while holding the lock to prevent use-after-free
            const RobotsInfo info = it->second;
            lock.unlock(); 
            
            auto now = std::chrono::steady_clock::now();
            if (!info.is_valid || info.last_http_status == 403 || info.last_http_status == 404 || now - info.timestamp > cache_expiry_) {
                return RobotsCheckResult::DEFERRED_FETCH_STARTED;
            }

            // The rest of the logic can now happen lock-free with our copy of the info
            std::vector<std::string> allowed_rules;
            std::vector<std::string> disallowed_rules;
            {
                ZoneScopedN("Robots Rule Parsing");
                parse_rules(info.content, user_agent, allowed_rules, disallowed_rules);
            }

            size_t max_disallow_len = 0;
            bool disallowed = false;
            for (const auto& rule : disallowed_rules) {
                if (path.rfind(rule, 0) == 0 && rule.length() > max_disallow_len) {
                    max_disallow_len = rule.length();
                    disallowed = true;
                }
            }

            size_t max_allow_len = 0;
            bool allowed = false;
            for (const auto& rule : allowed_rules) {
                if (path.rfind(rule, 0) == 0 && rule.length() > max_allow_len) {
                    max_allow_len = rule.length();
                    allowed = true;
                }
            }

            if (disallowed) {
                if (allowed && max_allow_len > max_disallow_len) {
                    return RobotsCheckResult::ALLOWED;
                }
                return RobotsCheckResult::DISALLOWED;
            }
            return RobotsCheckResult::ALLOWED;
        }
    } // Mutex is released here if we didn't find the entry in the cache

    //
    // === PASS 2: Not in memory, perform slow DB read OUTSIDE the lock ===
    //
    RobotsInfo loaded_info;
    bool loaded_from_db = false;
    {
        ZoneScopedN("Robots DB Load");
        std::string value;
        if (db_->Get(rocksdb::ReadOptions(), domain, &value).ok()) {
            loaded_info = deserialize(value);
            loaded_from_db = true;
        }
    }

    //
    // === PASS 3: Re-lock briefly to insert the loaded data into the cache ===
    //
    if (loaded_from_db) {
        std::unique_lock<std::mutex> lock(mutex_);
        // It's possible another thread loaded this between our Pass 1 and Pass 3.
        // The find-and-insert is still faster than re-processing.
        cache_[domain] = loaded_info;
        lock.unlock();

        // Now that it's in the cache, we can just call the function again.
        // This avoids duplicating the rule parsing logic and is very clean.
        return is_allowed(domain, path, user_agent);
    }
    
    //
    // === PASS 4: Entry not in memory or on disk, must fetch ===
    //
    {
        std::lock_guard<std::mutex> lock(mutex_);
        // Create a placeholder to prevent other threads from trying to fetch it too.
        cache_[domain] = RobotsInfo{}; 
    }
    return RobotsCheckResult::DEFERRED_FETCH_STARTED;
}

void RobotsTxtCache::update_cache(const std::string& domain, const std::string& content, int http_status) {
    RobotsInfo info;
    info.content = content;
    info.timestamp = std::chrono::steady_clock::now();
    info.last_http_status = http_status;
    info.is_valid = (http_status == 200);

    // Parse crawl-delay here
    std::vector<std::string> allowed, disallowed;
    parse_rules(content, "*", allowed, disallowed); // Crawl-delay is usually global
    
    // Parse sitemaps from robots.txt content
    if (info.is_valid && !content.empty()) {
        info.sitemaps = parse_sitemaps_from_robots(content);
        info.sitemaps_parsed = true;
    } else {
        info.sitemaps_parsed = false;
    }

    {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_[domain] = info;
    }
    db_->Put(rocksdb::WriteOptions(), domain, serialize(info));
}

void RobotsTxtCache::invalidate_for_domain(const std::string& domain) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.erase(domain);
    }
    db_->Delete(rocksdb::WriteOptions(), domain);
}

// *** NEW PARSING FUNCTION ***
bool RobotsTxtCache::parse_rules(const std::string& content, const std::string& user_agent, 
                                 std::vector<std::string>& allowed, std::vector<std::string>& disallowed) const {
    std::stringstream ss(content);
    std::string line;
    std::string current_ua;
    bool our_ua_is_active = false;
    bool global_ua_is_active = false;

    while (std::getline(ss, line)) {
        // Trim whitespace and remove comments
        line.erase(0, line.find_first_not_of(" \t"));
        line.erase(line.find_last_not_of(" \t") + 1);
        size_t comment_pos = line.find('#');
        if (comment_pos != std::string::npos) {
            line = line.substr(0, comment_pos);
        }
        if (line.empty()) continue;

        // Convert to lower case for case-insensitive matching
        std::string line_lower = line;
        std::transform(line_lower.begin(), line_lower.end(), line_lower.begin(),
                       [](unsigned char c){ return std::tolower(c); });

        // Check for User-agent
        if (line_lower.rfind("user-agent:", 0) == 0) {
            current_ua = line.substr(11);
            current_ua.erase(0, current_ua.find_first_not_of(" \t"));
            our_ua_is_active = (current_ua == user_agent);
            global_ua_is_active = (current_ua == "*");
        }
        // Check for Disallow
        else if (line_lower.rfind("disallow:", 0) == 0) {
            if (our_ua_is_active || global_ua_is_active) {
                std::string path = line.substr(9);
                path.erase(0, path.find_first_not_of(" \t"));
                if (!path.empty()) {
                    disallowed.push_back(path);
                }
            }
        }
        // Check for Allow
        else if (line_lower.rfind("allow:", 0) == 0) {
            if (our_ua_is_active || global_ua_is_active) {
                std::string path = line.substr(6);
                path.erase(0, path.find_first_not_of(" \t"));
                 if (!path.empty()) {
                    allowed.push_back(path);
                }
            }
        }
    }
    return true;
}

// *** NEW SITEMAP PARSING FUNCTION ***
std::vector<SitemapInfo> RobotsTxtCache::parse_sitemaps_from_robots(const std::string& content) const {
    std::vector<SitemapInfo> sitemaps;
    std::stringstream ss(content);
    std::string line;

    while (std::getline(ss, line)) {
        // Trim whitespace and remove comments
        line.erase(0, line.find_first_not_of(" \t"));
        line.erase(line.find_last_not_of(" \t") + 1);
        size_t comment_pos = line.find('#');
        if (comment_pos != std::string::npos) {
            line = line.substr(0, comment_pos);
        }
        if (line.empty()) continue;

        // Convert to lower case for case-insensitive matching
        std::string line_lower = line;
        std::transform(line_lower.begin(), line_lower.end(), line_lower.begin(),
                       [](unsigned char c){ return std::tolower(c); });

        // Check for Sitemap
        if (line_lower.rfind("sitemap:", 0) == 0) {
            std::string sitemap_url = line.substr(8); // Remove "sitemap:"
            sitemap_url.erase(0, sitemap_url.find_first_not_of(" \t"));
            sitemap_url.erase(sitemap_url.find_last_not_of(" \t\r\n") + 1);
            
            if (!sitemap_url.empty()) {
                // Assign priority based on sitemap type heuristics
                float priority = 0.5f; // Default
                if (sitemap_url.find("index") != std::string::npos) {
                    priority = 0.9f; // Sitemap indexes are usually high priority
                } else if (sitemap_url.find("news") != std::string::npos) {
                    priority = 0.8f; // News sitemaps are frequently updated
                } else if (sitemap_url.find("image") != std::string::npos || 
                          sitemap_url.find("video") != std::string::npos) {
                    priority = 0.6f; // Media sitemaps are medium priority
                }
                
                sitemaps.emplace_back(sitemap_url, priority);
            }
        }
    }
    
    return sitemaps;
}

std::vector<SitemapInfo> RobotsTxtCache::get_sitemaps_for_domain(const std::string& domain) {
    //
    // === PASS 1: Quick, optimistic check with a short lock ===
    //
    {
        std::unique_lock<std::mutex> lock(mutex_);
        auto it = cache_.find(domain);
        if (it != cache_.end()) {
            const auto& info = it->second;
            // Unlock immediately after we have the info we need.
            lock.unlock(); 
            
            auto now = std::chrono::steady_clock::now();
            if (info.is_valid && info.sitemaps_parsed && now - info.timestamp <= cache_expiry_) {
                return info.sitemaps; // Return copy
            }
        }
    } // Mutex is released here if we didn't find valid entry in the cache

    //
    // === PASS 2: Not in memory or expired, perform slow DB read OUTSIDE the lock ===
    //
    RobotsInfo loaded_info;
    bool loaded_from_db = false;
    {
        std::string value;
        if (db_->Get(rocksdb::ReadOptions(), domain, &value).ok()) {
            loaded_info = deserialize(value);
            loaded_from_db = true;
        }
    }

    //
    // === PASS 3: Re-lock briefly to insert the loaded data into the cache ===
    //
    if (loaded_from_db) {
        std::unique_lock<std::mutex> lock(mutex_);
        // It's possible another thread loaded this between our Pass 1 and Pass 3.
        cache_[domain] = loaded_info;
        lock.unlock();

        // Check if loaded data is still valid
        auto now = std::chrono::steady_clock::now();
        if (loaded_info.is_valid && loaded_info.sitemaps_parsed && now - loaded_info.timestamp <= cache_expiry_) {
            return loaded_info.sitemaps;
        }
    }
    
    // No valid sitemaps found
    return {};
}

bool RobotsTxtCache::has_robots_for_domain(const std::string& domain) const {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = cache_.find(domain);
        if (it != cache_.end()) {
            auto now = std::chrono::steady_clock::now();
            return (it->second.is_valid && now - it->second.timestamp <= cache_expiry_);
        }
    }
    
    // Check DB
    std::string value;
    if (db_->Get(rocksdb::ReadOptions(), domain, &value).ok()) {
        auto info = deserialize(value);
        auto now = std::chrono::steady_clock::now();
        return (info.is_valid && now - info.timestamp <= cache_expiry_);
    }
    
    return false;
}

int RobotsTxtCache::get_crawl_delay(const std::string& domain) const {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = cache_.find(domain);
        if (it != cache_.end()) {
            auto now = std::chrono::steady_clock::now();
            if (it->second.is_valid && now - it->second.timestamp <= cache_expiry_) {
                return it->second.crawl_delay;
            }
        }
    }
    
    // Check DB
    std::string value;
    if (db_->Get(rocksdb::ReadOptions(), domain, &value).ok()) {
        auto info = deserialize(value);
        auto now = std::chrono::steady_clock::now();
        if (info.is_valid && now - info.timestamp <= cache_expiry_) {
            return info.crawl_delay;
        }
    }
    
    return 0; // No delay
}