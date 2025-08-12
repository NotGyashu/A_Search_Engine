#pragma once

#include <string>
#include <unordered_map>
#include <chrono>
#include <memory>
#include <fstream>
#include <vector>


/**
 * 🧡 PER-DOMAIN CONFIGURATION SUPPORT
 * Domain-specific crawling   rules
 */

namespace DomainConfiguration {

struct CrawlFrequencyConfig {
    std::chrono::hours crawl_interval{24}; // Default 24 hours
    bool use_freshness_based{true};        // Use content change frequency
    float frequency_multiplier{1.0f};      // Multiply detected frequency
    
    CrawlFrequencyConfig() = default;
    CrawlFrequencyConfig(int hours) : crawl_interval(hours), use_freshness_based(false) {}
};

struct DomainConfig {
    // Crawling configuration
    CrawlFrequencyConfig crawl_frequency;
    
    
    // Language filtering
    std::vector<std::string> language_whitelist; // Empty = allow all
    
    // Custom rules
    bool enabled{true};
    float priority_multiplier{1.0f};
    
    DomainConfig() = default;
};

/**
 * Domain configuration manager
 * Loads and manages per-domain settings
 */
class DomainConfigManager {
private:
    std::unordered_map<std::string, DomainConfig> domain_configs_;
    DomainConfig default_config_;
    std::string config_file_path_;
    
    // Helper methods for JSON parsing
    bool load_from_json(const std::string& file_path);
    bool load_from_yaml(const std::string& file_path);
    void parse_json_config(const std::string& json_content);
    DomainConfig parse_domain_config_json_modern(const void* domain_json);
    
    // Configuration parsing helpers
    CrawlFrequencyConfig parse_crawl_frequency(const std::string& config_section);
    
public:
    DomainConfigManager();
    ~DomainConfigManager() = default;
    
    // Configuration loading
    bool load_config(const std::string& file_path);
    bool reload_config();
    
    // Domain configuration access
    const DomainConfig& get_config_for_domain(const std::string& domain) const;
    bool has_domain_config(const std::string& domain) const;
    
    // Configuration management
    void set_domain_config(const std::string& domain, const DomainConfig& config);
    void remove_domain_config(const std::string& domain);
    
    // Crawl frequency helpers
    std::chrono::system_clock::time_point get_next_crawl_time(const std::string& domain,
                                                             std::chrono::system_clock::time_point last_crawl,
                                                             float detected_frequency = 0.0f) const;
    
    bool should_crawl_now(const std::string& domain,
                         std::chrono::system_clock::time_point last_crawl,
                         float detected_frequency = 0.0f) const;
    
    // Statistics and debugging
    void print_domain_configs() const;
    size_t get_configured_domain_count() const { return domain_configs_.size(); }
    
    // Default configuration access
    const DomainConfig& get_default_config() const { return default_config_; }
    void set_default_config(const DomainConfig& config) { default_config_ = config; }
};

/**
 * Global domain configuration instance
 */
extern std::unique_ptr<DomainConfigManager> g_domain_config_manager;

// Utility functions for domain extraction
std::string extract_domain_from_url(const std::string& url);
std::string normalize_domain(const std::string& domain);

} // namespace DomainConfiguration
