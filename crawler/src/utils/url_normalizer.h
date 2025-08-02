#pragma once

#include <string>
#include <unordered_set>

// Comprehensive URL normalizer (REGEX-FREE)
class UrlNormalizer {
private:
   
    static std::unordered_set<std::string> tracking_params_;

public:
    static std::string normalize(const std::string& url);
    static std::string resolve_relative(const std::string& base_url, const std::string& relative_url);
    static std::string extract_domain(const std::string& url);
    static std::string extract_path(const std::string& url);
    static bool is_valid_url(const std::string& url);
    
    // Fast helper functions
    static std::string normalize_domain_case(std::string_view domain);
    static std::string clean_path_slashes(std::string_view path);
    static std::string remove_tracking_params(std::string_view query);
};
