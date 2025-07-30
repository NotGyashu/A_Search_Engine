#pragma once

#include <unordered_map>
#include <unordered_set>
#include <chrono>
#include <mutex>
#include <string>

class DomainBlacklist {
private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> blacklist_;
    const std::chrono::seconds cooldown_{60};
    std::unordered_set<std::string> permanent_blacklist_;

public:
    bool is_blacklisted(const std::string& domain) const;
    void add_temporary(const std::string& domain);
    void add_permanent(const std::string& domain);
    void cleanup_expired(); // New method to clean expired entries
    size_t size() const;
    void load_from_file(const std::string& filename);
};
