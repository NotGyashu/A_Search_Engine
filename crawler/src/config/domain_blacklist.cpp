#include "domain_blacklist.h"
#include <fstream>
#include <iostream>

bool DomainBlacklist::is_blacklisted(const std::string& domain) const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    // Check permanent blacklist first
    if (permanent_blacklist_.count(domain)) {
        return true;
    }
    
    // Check temporary blacklist with cooldown
    auto it = blacklist_.find(domain);
    if (it != blacklist_.end()) {
        auto now = std::chrono::steady_clock::now();
        if (now - it->second < cooldown_) {
            return true;
        } else {
            // Cooldown expired - can't modify in const method, will be cleaned up later
            return false;
        }
    }
    
    return false;
}

void DomainBlacklist::add_temporary(const std::string& domain) {
    std::lock_guard<std::mutex> lock(mutex_);
    blacklist_[domain] = std::chrono::steady_clock::now();
}

void DomainBlacklist::add_permanent(const std::string& domain) {
    std::lock_guard<std::mutex> lock(mutex_);
    permanent_blacklist_.insert(domain);
}

void DomainBlacklist::cleanup_expired() {
    std::lock_guard<std::mutex> lock(mutex_);
    auto now = std::chrono::steady_clock::now();
    
    auto it = blacklist_.begin();
    while (it != blacklist_.end()) {
        if (now - it->second >= cooldown_) {
            it = blacklist_.erase(it);
        } else {
            ++it;
        }
    }
}

size_t DomainBlacklist::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return blacklist_.size() + permanent_blacklist_.size();
}
