#include "enriched_storage.h"
#include "content_hash.h"
#include "utility_functions.h"
#include "url_normalizer.h"
#include "html_document.h"
#include "snippet_extractor.h"
#include "domain_config.h"
#include "time_utils.h"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <filesystem>
#include <ctime>

// External global components (declared in crawler_main.cpp)
extern std::unique_ptr<SnippetExtraction::SnippetExtractor> snippet_extractor;
extern std::unique_ptr<DomainConfiguration::DomainConfigManager> domain_config_manager;

namespace CrawlScheduling {

EnhancedFileStorageManager::EnhancedFileStorageManager(const std::string& base_path, 
                                                      std::shared_ptr<CrawlMetadataStore> metadata_store)
    : base_path_(base_path), metadata_store_(metadata_store) {
    
    // Ensure base directory exists
    ensure_directory_exists(base_path_);
    
    // Start storage worker thread
    storage_thread_ = std::thread(&EnhancedFileStorageManager::enhanced_storage_worker, this);
}

EnhancedFileStorageManager::~EnhancedFileStorageManager() {
    // Signal shutdown
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        shutdown_ = true;
    }
    queue_cv_.notify_all();
    
    // Wait for worker thread to finish
    if (storage_thread_.joinable()) {
        storage_thread_.join();
    }
}

void EnhancedFileStorageManager::enhanced_storage_worker() {
    while (!shutdown_) {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        
        // Wait for batches or shutdown
        queue_cv_.wait(lock, [this] { return !storage_queue_.empty() || shutdown_; });
        
        if (!storage_queue_.empty()) {
            auto batch = storage_queue_.front();
            storage_queue_.pop();
            lock.unlock();
            
            // Process batch without holding locks
            std::string batch_filename = "batch_" + TimeUtils::current_timestamp() + "_" + 
                                       batch.batch_id + ".json";
            std::string filepath = base_path_ + "/" + batch_filename;
            
            std::ofstream file(filepath);
            if (!file.is_open()) {
                std::cerr << "Failed to open file for writing: " << filepath << std::endl;
                continue;
            }
            
            // Simple array format like the original, but with metadata
            file << "[\n";
            
            for (size_t i = 0; i < batch.data.size(); ++i) {
                if (i > 0) file << ",\n";
                file << batch.data[i].to_json();
            }
            
            file << "\n]\n";
            
            file.close();
            
            // Note: Removed verbose logging for performance
        }
    }
}

void EnhancedFileStorageManager::save_enriched_batch(const std::vector<EnrichedPageData>& batch) {
    if (batch.empty()) return;
    
    EnrichedStorageBatch storage_batch;
    storage_batch.data = batch;
    storage_batch.batch_id = std::to_string(batch_counter_++);
    
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        storage_queue_.push(storage_batch);
    }
    
    queue_cv_.notify_one();
}

void EnhancedFileStorageManager::save_html_batch_with_metadata(
    const std::vector<std::pair<std::string, std::string>>& simple_batch) {
    
    if (simple_batch.empty()) return;
    
    std::vector<EnrichedPageData> enriched_batch;
    enriched_batch.reserve(simple_batch.size());
    
    for (const auto& [url, content] : simple_batch) {
        EnrichedPageData enriched = create_enriched_data(url, content);
        enriched_batch.push_back(std::move(enriched));
    }
    
    save_enriched_batch(enriched_batch);
}

EnrichedPageData EnhancedFileStorageManager::create_enriched_data(const std::string& url, 
                                                                 const std::string& content,
                                                                 const std::string& title, 
                                                                 int depth,
                                                                 int http_status) {
    // Get metadata from store
    UrlMetadata* metadata = metadata_store_->get_or_create_metadata(url);
    
    // Create enriched data
    EnrichedPageData enriched(url, content, metadata);
    
    // Set additional fields
    enriched.domain = UrlNormalizer::extract_domain(url);
    if (title.empty()) {
        HtmlDocument doc(content);
        enriched.title = doc.getTitle();
    } else {
        enriched.title = title;
    }
    enriched.depth = depth;
    enriched.http_status_code = http_status;
    enriched.content_length = content.length();
    
    // Extract high-quality snippet for search results
    if (snippet_extractor && domain_config_manager) {
        try {
            // Get domain-specific config for snippet extraction
            auto domain_config = domain_config_manager->get_config_for_domain(enriched.domain);
            
            // Extract snippet using the configured extractor
            auto snippet_result = snippet_extractor->extract_snippet(
                content, url, domain_config.snippet_config
            );
            enriched.text_snippet = snippet_result.text_snippet;
        } catch (const std::exception& e) {
            std::cerr << "Snippet extraction failed for " << url << ": " << e.what() << std::endl;
            enriched.text_snippet = ""; // Fallback to empty snippet
        }
    } else {
        enriched.text_snippet = ""; // No snippet extractor available
    }
    
    // Generate and update content hash
    std::string new_hash = ContentHashing::FastContentHasher::hash_key_content(content);
    if (enriched.content_hash != new_hash) {
        // Content changed - update metadata
        metadata_store_->update_after_crawl(url, new_hash);
        
        // Refresh metadata in enriched data
        metadata = metadata_store_->get_or_create_metadata(url);
        enriched.content_hash = metadata->content_hash;
        enriched.last_crawl_time = metadata->last_crawl_time;
        enriched.previous_change_time = metadata->previous_change_time;
        enriched.expected_next_crawl = metadata->expected_next_crawl;
        enriched.backoff_multiplier = metadata->backoff_multiplier;
        enriched.crawl_count = metadata->crawl_count;
        enriched.change_frequency = metadata->change_frequency;
    }
    
    return enriched;
}

void EnhancedFileStorageManager::flush() {
    // Wait for all pending storage operations to complete
    std::unique_lock<std::mutex> lock(queue_mutex_);
    queue_cv_.wait(lock, [this] { return storage_queue_.empty(); });
}

bool EnhancedFileStorageManager::ensure_directory_exists(const std::string& path) {
    try {
        return std::filesystem::create_directories(path) || std::filesystem::exists(path);
    } catch (const std::exception& e) {
        std::cerr << "Failed to create directory " << path << ": " << e.what() << std::endl;
        return false;
    }
}

} // namespace CrawlScheduling
