#include "robots_txt_cache.h"
#include <algorithm>
#include <sstream>
#include <iostream>

RobotsTxtCache::RobotsTxtCache() {}

RobotsCheckResult RobotsTxtCache::is_allowed(const std::string& domain, const std::string& path, const std::string& user_agent) {
    std::unique_lock<std::mutex> lock(mutex_);
    
    auto it = cache_.find(domain);
    if (it != cache_.end()) {
        // Entry found in cache.
        const auto& info = it->second;
        
        // Check if cache entry is expired.
        auto now = std::chrono::steady_clock::now();
        if (now - info.timestamp > cache_expiry_) {
            cache_.erase(it);
            // Fall through to "not found" case to trigger a fresh fetch.
        } else {
            // Entry is valid and not expired.
            if (!info.is_valid) {
                // A previous fetch failed. Allow crawling by default.
                return RobotsCheckResult::ALLOWED;
            }
            
            // Parse the rules and check if the path is disallowed.
            std::istringstream stream(info.content);
            std::string line;
            bool in_relevant_section = false;
            
            while (std::getline(stream, line)) {
                std::string lower_line = line;
                std::transform(lower_line.begin(), lower_line.end(), lower_line.begin(), ::tolower);
                
                if (lower_line.rfind("user-agent:", 0) == 0) {
                    std::string agent = line.substr(11);
                    agent.erase(0, agent.find_first_not_of(" \t"));
                    in_relevant_section = (agent == "*" || agent == user_agent);
                } else if (in_relevant_section && lower_line.rfind("disallow:", 0) == 0) {
                    std::string disallowed = line.substr(9);
                    disallowed.erase(0, disallowed.find_first_not_of(" \t"));
                    if (!disallowed.empty() && (disallowed == "/" || path.rfind(disallowed, 0) == 0)) {
                        return RobotsCheckResult::DISALLOWED;
                    }
                }
            }
            
            // Allowed by default if no disallow rule matched.
            return RobotsCheckResult::ALLOWED;
        }
    }
    
    // Entry not in cache or expired, need to fetch.
    // Create a placeholder to prevent other threads from starting the same fetch.
    RobotsInfo placeholder;
    placeholder.is_valid = false; // Mark as invalid until content arrives.
    placeholder.timestamp = std::chrono::steady_clock::now();
    cache_[domain] = std::move(placeholder);
    
    // Signal the caller that a fetch is required.
    return RobotsCheckResult::DEFERRED_FETCH_STARTED;
}

void RobotsTxtCache::update_cache(const std::string& domain, const std::string& content, bool fetch_successful) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = cache_.find(domain);
    if (it != cache_.end()) {
        // Update the existing placeholder.
        it->second.content = content;
        it->second.timestamp = std::chrono::steady_clock::now();
        it->second.is_valid = fetch_successful;
    } else {
        // Should not happen if is_allowed is called first, but handle for safety.
        RobotsInfo info;
        info.content = content;
        info.timestamp = std::chrono::steady_clock::now();
        info.is_valid = fetch_successful;
        cache_[domain] = std::move(info);
    }
}

// clear_expired and size methods remain largely the same.
void RobotsTxtCache::clear_expired() {
    std::lock_guard<std::mutex> lock(mutex_);
    auto now = std::chrono::steady_clock::now();
    for (auto it = cache_.begin(); it != cache_.end(); ) {
        if (now - it->second.timestamp > cache_expiry_) {
            it = cache_.erase(it);
        } else {
            ++it;
        }
    }
}

size_t RobotsTxtCache::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return cache_.size();
}