#pragma once

#include <string>
#include <regex>
#include <unordered_set>

// Comprehensive URL normalizer
class UrlNormalizer {
private:
    static std::regex protocol_regex_;
    static std::regex domain_regex_;
    static std::regex path_cleanup_regex_;
    static std::unordered_set<std::string> tracking_params_;

public:
    static std::string normalize(const std::string& url);
    static std::string resolve_relative(const std::string& base_url, const std::string& relative_url);
    static std::string extract_domain(const std::string& url);
    static std::string extract_path(const std::string& url);
    static bool is_valid_url(const std::string& url);
};
