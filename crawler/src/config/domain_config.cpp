#include "domain_config.h"
#include <iostream>
#include <sstream>
#include <algorithm>
#include <nlohmann/json.hpp>
#include "url_normalizer.h"

using json = nlohmann::json;

namespace DomainConfiguration {

// Global instance
std::unique_ptr<DomainConfigManager> g_domain_config_manager = nullptr;

DomainConfigManager::DomainConfigManager() {
    // Initialize default configuration
    default_config_.crawl_frequency = CrawlFrequencyConfig{};
    default_config_.enabled = true;
    default_config_.priority_multiplier = 1.0f;
}

bool DomainConfigManager::load_config(const std::string& file_path) {
    config_file_path_ = file_path;
    
    // Determine file format by extension (C++17 compatible)
    if (file_path.size() >= 5 && file_path.substr(file_path.size() - 5) == ".json") {
        return load_from_json(file_path);
    } else if ((file_path.size() >= 5 && file_path.substr(file_path.size() - 5) == ".yaml") ||
               (file_path.size() >= 4 && file_path.substr(file_path.size() - 4) == ".yml")) {
        return load_from_yaml(file_path);
    }
    
    std::cerr << "⚠️  Unsupported domain config file format: " << file_path << std::endl;
    return false;
}

bool DomainConfigManager::load_from_json(const std::string& file_path) {
    try {
        std::ifstream file(file_path);
        if (!file.is_open()) {
            std::cerr << "⚠️  Could not open domain config file: " << file_path << std::endl;
            return false;
        }
        
        std::string json_content((std::istreambuf_iterator<char>(file)),
                                std::istreambuf_iterator<char>());
        file.close();
        
        if (json_content.empty()) {
            std::cerr << "⚠️  Empty domain config file: " << file_path << std::endl;
            return false;
        }
        
        parse_json_config(json_content);
        std::cout << "✅ Loaded domain configurations from " << file_path << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Error loading domain config: " << e.what() << std::endl;
        return false;
    }
}

bool DomainConfigManager::load_from_yaml(const std::string& file_path) {
    // Basic YAML support - for now, fall back to JSON
    std::cerr << "⚠️  YAML support not yet implemented. Please use JSON format." << std::endl;
    return false;
}

void DomainConfigManager::parse_json_config(const std::string& json_content) {
    try {
        json config_json = json::parse(json_content);
        
        domain_configs_.clear();
        
        // Check if domains section exists
        if (!config_json.contains("domains") || !config_json["domains"].is_object()) {
            std::cerr << "⚠️  No 'domains' section found in config" << std::endl;
            return;
        }
        
        const auto& domains = config_json["domains"];
        
        // Parse each domain configuration
        for (const auto& [domain, domain_config] : domains.items()) {
            try {
                DomainConfig config = parse_domain_config_json_modern(&domain_config);
                domain_configs_[normalize_domain(domain)] = config;
                // std::cout << "   Loaded config for domain: " << domain << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "⚠️  Error parsing config for domain " << domain << ": " << e.what() << std::endl;
            }
        }
    } catch (const json::parse_error& e) {
        std::cerr << "❌ JSON parse error: " << e.what() << std::endl;
        throw;
    }
}

DomainConfig DomainConfigManager::parse_domain_config_json_modern(const void* domain_json_ptr) {
    const auto& domain_json = *static_cast<const json*>(domain_json_ptr);
    DomainConfig config = default_config_; // Start with defaults
    
    // Parse crawl_frequency_limit
    if (domain_json.contains("crawl_frequency_limit") && domain_json["crawl_frequency_limit"].is_string()) {
        std::string freq_str = domain_json["crawl_frequency_limit"];
        
        // Parse time units (e.g., "6h", "1d", "30m")
        if (freq_str.length() >= 2) {
            char unit = freq_str.back();
            std::string value_str = freq_str.substr(0, freq_str.length() - 1);
            
            try {
                int value = std::stoi(value_str);
                
                switch (unit) {
                    case 'h':
                    case 'H':
                        config.crawl_frequency = CrawlFrequencyConfig(value);
                        break;
                    case 'd':
                    case 'D':
                        config.crawl_frequency = CrawlFrequencyConfig(value * 24);
                        break;
                    case 'm':
                    case 'M':
                        config.crawl_frequency = CrawlFrequencyConfig(std::max(1, value / 60));
                        break;
                    default:
                        std::cerr << "⚠️  Unknown time unit: " << unit << std::endl;
                }
            } catch (const std::exception& e) {
                std::cerr << "⚠️  Invalid frequency value: " << freq_str << std::endl;
            }
        }
    }
    
    // Parse language_whitelist
    if (domain_json.contains("language_whitelist") && domain_json["language_whitelist"].is_array()) {
        config.language_whitelist.clear();
        for (const auto& lang : domain_json["language_whitelist"]) {
            if (lang.is_string()) {
                config.language_whitelist.push_back(lang.get<std::string>());
            }
        }
    }
    
    // Parse enabled flag
    if (domain_json.contains("enabled") && domain_json["enabled"].is_boolean()) {
        config.enabled = domain_json["enabled"];
    }
    
    // Parse priority_multiplier
    if (domain_json.contains("priority_multiplier") && domain_json["priority_multiplier"].is_number()) {
        config.priority_multiplier = domain_json["priority_multiplier"];
    }
    
    return config;
}

bool DomainConfigManager::reload_config() {
    if (config_file_path_.empty()) {
        return false;
    }
    return load_config(config_file_path_);
}

const DomainConfig& DomainConfigManager::get_config_for_domain(const std::string& domain) const {
    std::string normalized = normalize_domain(domain);
    auto it = domain_configs_.find(normalized);
    if (it != domain_configs_.end()) {
        return it->second;
    }
    return default_config_;
}

bool DomainConfigManager::has_domain_config(const std::string& domain) const {
    std::string normalized = normalize_domain(domain);
    return domain_configs_.find(normalized) != domain_configs_.end();
}

void DomainConfigManager::set_domain_config(const std::string& domain, const DomainConfig& config) {
    domain_configs_[normalize_domain(domain)] = config;
}

void DomainConfigManager::remove_domain_config(const std::string& domain) {
    domain_configs_.erase(normalize_domain(domain));
}

std::chrono::system_clock::time_point DomainConfigManager::get_next_crawl_time(
    const std::string& domain,
    std::chrono::system_clock::time_point last_crawl,
    float detected_frequency) const {
    
    const DomainConfig& config = get_config_for_domain(domain);
    
    if (config.crawl_frequency.use_freshness_based && detected_frequency > 0.0f) {
        // Use detected frequency with multiplier
        auto interval = std::chrono::hours(static_cast<int>(24.0f / (detected_frequency * config.crawl_frequency.frequency_multiplier)));
        return last_crawl + interval;
    } else {
        // Use fixed interval
        return last_crawl + config.crawl_frequency.crawl_interval;
    }
}

bool DomainConfigManager::should_crawl_now(const std::string& domain,
                                          std::chrono::system_clock::time_point last_crawl,
                                          float detected_frequency) const {
    auto next_crawl_time = get_next_crawl_time(domain, last_crawl, detected_frequency);
    return std::chrono::system_clock::now() >= next_crawl_time;
}

void DomainConfigManager::print_domain_configs() const {
    std::cout << "📊 Domain Configuration Summary:\n";
    std::cout << "   Total configured domains: " << domain_configs_.size() << "\n";
    
    for (const auto& [domain, config] : domain_configs_) {
        std::cout << "   Domain: " << domain << "\n";
        std::cout << "     Crawl interval: " << config.crawl_frequency.crawl_interval.count() << "h\n";
        std::cout << "     Use freshness: " << (config.crawl_frequency.use_freshness_based ? "yes" : "no") << "\n";
        std::cout << "     Language filter: " << config.language_whitelist.size() << " languages\n";
        std::cout << "     Enabled: " << (config.enabled ? "yes" : "no") << "\n";
    }
}

// Utility functions
std::string normalize_domain(const std::string& domain) {
    std::string normalized = domain;
    
    // Convert to lowercase
    std::transform(normalized.begin(), normalized.end(), normalized.begin(), ::tolower);
    
    // Remove www. prefix (C++17 compatible)
    if (normalized.size() >= 4 && normalized.substr(0, 4) == "www.") {
        normalized = normalized.substr(4);
    }
    
    return normalized;
}

} // namespace DomainConfiguration
