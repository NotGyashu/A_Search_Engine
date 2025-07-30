#pragma once

#include <string>
#include <chrono>
#include <cmath>

struct UrlInfo {
    std::string url;
    float priority;
    int depth;
    std::string referring_domain;
    std::chrono::steady_clock::time_point discovered_time;
    
    UrlInfo(const std::string& u, float p = 0.5f, int d = 0, const std::string& ref = "")
        : url(u), priority(p), depth(d), referring_domain(ref), 
          discovered_time(std::chrono::steady_clock::now()) {}
};

// Priority queue comparator
struct UrlPriorityComparator {
    bool operator()(const UrlInfo& a, const UrlInfo& b) const {
        if (std::abs(a.priority - b.priority) > 0.01f) {
            return a.priority < b.priority; // Higher priority first
        }
        return a.depth > b.depth; // Lower depth first
    }
};
