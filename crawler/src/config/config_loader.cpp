#include "config_loader.h"
#include <sstream>
#include <algorithm>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>

using json = nlohmann::json;

namespace ConfigLoader {

std::vector<std::string> load_seed_urls(const std::string& config_path) {
    std::ifstream file(config_path);
    if (!file.is_open()) {
        std::cerr << "Warning: Could not open seeds config file: " << config_path << std::endl;
        std::cout << "Falling back to empty seed list. Crawler will depend on RSS feeds and sitemaps." << std::endl;
        return {};
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    std::string content = buffer.str();
    
    auto seeds = JsonParser::parse_string_array(content);
    std::cout << "✅ Loaded " << seeds.size() << " seed URLs from " << config_path << std::endl;
    return seeds;
}

std::vector<FeedConfig> load_feed_configs(const std::string& config_path) {
    std::ifstream file(config_path);
    if (!file.is_open()) {
        std::cerr << "Warning: Could not open RSS feeds config file: " << config_path << std::endl;
        return {};
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    std::string content = buffer.str();
    
    auto feeds = JsonParser::parse_feed_array(content);
    std::cout << "✅ Loaded " << feeds.size() << " RSS/Atom feeds from " << config_path << std::endl;
    return feeds;
}


namespace JsonParser {

std::string remove_comments(const std::string& json_content) {
    std::stringstream result;
    std::istringstream stream(json_content);
    std::string line;
    
    while (std::getline(stream, line)) {
        // Remove comments starting with // or #
        size_t comment_pos = line.find("//");
        if (comment_pos == std::string::npos) {
            comment_pos = line.find("#");
        }
        
        if (comment_pos != std::string::npos) {
            line = line.substr(0, comment_pos);
        }
        
        // Trim trailing whitespace
        line.erase(std::find_if(line.rbegin(), line.rend(), [](int ch) {
            return !std::isspace(ch);
        }).base(), line.end());
        
        if (!line.empty()) {
            result << line << "\n";
        }
    }
    
    return result.str();
}

std::vector<std::string> parse_string_array(const std::string& json_content) {
    std::vector<std::string> result;
    try {
        json arr = json::parse(json_content);
        if (!arr.is_array()) return result;

        for (const auto& el : arr) {
            if (el.is_string()) result.push_back(el.get<std::string>());
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Failed to parse seeds.json: " << e.what() << std::endl;
    }
    return result;
}

std::vector<FeedConfig> parse_feed_array(const std::string& json_content) {
    std::vector<FeedConfig> result;
    try {
        json feed_array = json::parse(json_content);

        for (const auto& entry : feed_array) {
            if (!entry.contains("url")) continue;
            std::string url = entry["url"];
            int priority = entry.value("priority", 5);          // default priority = 5
            int interval = entry.value("poll_interval", 10);    // default = 10 min
            result.emplace_back(url, interval, priority);
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Failed to parse rss_feeds.json: " << e.what() << std::endl;
    }
    return result;
}


} // namespace JsonParser
} // namespace ConfigLoader
