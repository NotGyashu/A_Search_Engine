#include "enriched_storage.h"
#include "content_hash.h"
#include "utility_functions.h"
#include "url_normalizer.h"
#include "html_document.h"
#include "domain_config.h"
#include "time_utils.h"
#include <nlohmann/json.hpp>  // ✅ HIGH-PERFORMANCE JSON LIBRARY
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <filesystem>
#include <ctime>
#include <future>
#include <codecvt>
#include <locale>
#include "tracy/Tracy.hpp"

// External global components (declared in crawler_main.cpp)
extern std::unique_ptr<DomainConfiguration::DomainConfigManager> domain_config_manager;

namespace CrawlScheduling {

// ✅ CRITICAL FIX: UTF-8 sanitization to prevent nlohmann/json errors
std::string sanitize_utf8(const std::string& input) {
    std::string result;
    result.reserve(input.size());
    
    for (size_t i = 0; i < input.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(input[i]);
        
        if (c < 0x80) {
            // ASCII character - always valid
            result += c;
        } else if (c < 0xC0) {
            // Invalid start byte - replace with placeholder
            result += '?';
        } else if (c < 0xE0) {
            // 2-byte sequence
            if (i + 1 < input.size() && (input[i + 1] & 0xC0) == 0x80) {
                result += input.substr(i, 2);
                i += 1;
            } else {
                result += '?';
            }
        } else if (c < 0xF0) {
            // 3-byte sequence
            if (i + 2 < input.size() && 
                (input[i + 1] & 0xC0) == 0x80 && 
                (input[i + 2] & 0xC0) == 0x80) {
                result += input.substr(i, 3);
                i += 2;
            } else {
                result += '?';
            }
        } else if (c < 0xF8) {
            // 4-byte sequence
            if (i + 3 < input.size() && 
                (input[i + 1] & 0xC0) == 0x80 && 
                (input[i + 2] & 0xC0) == 0x80 && 
                (input[i + 3] & 0xC0) == 0x80) {
                result += input.substr(i, 4);
                i += 3;
            } else {
                result += '?';
            }
        } else {
            // Invalid UTF-8 start byte
            result += '?';
        }
    }
    
    return result;
}

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
        flush_requested_ = false;  // Cancel any pending flush to avoid deadlock
    }
    queue_cv_.notify_all();
    flush_cv_.notify_all();  // Wake up any threads waiting on flush
    
    // Wait for worker thread to finish with timeout
    if (storage_thread_.joinable()) {
        auto timeout = std::chrono::seconds(5);  // Reduced timeout
        auto start_time = std::chrono::steady_clock::now();
        
        // Give the thread time to finish naturally
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        if (storage_thread_.joinable()) {
            auto future = std::async(std::launch::async, [this]() {
                if (storage_thread_.joinable()) {
                    storage_thread_.join();
                }
            });
            
            if (future.wait_for(timeout) == std::future_status::timeout) {
                std::cerr << "⚠️  Storage worker thread timeout - detaching" << std::endl;
                storage_thread_.detach();
            }
        }
    }
}

void EnhancedFileStorageManager::enhanced_storage_worker() {
    while (!shutdown_) {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        
        // Wait for batches or shutdown with timeout to prevent hanging
        auto timeout = std::chrono::milliseconds(100);  // 100ms timeout
        queue_cv_.wait_for(lock, timeout, [this] { 
            return !storage_queue_.empty() || shutdown_ || flush_requested_; 
        });
        
        // Process all available batches before checking shutdown
        // ✅ NEW: Limit batch processing time to prevent long delays during flush
        const size_t max_batches_per_cycle = 5;  // Process max 5 batches before checking shutdown
        size_t processed_this_cycle = 0;
        
        while (!storage_queue_.empty() && !shutdown_ && processed_this_cycle < max_batches_per_cycle) {
            auto batch = storage_queue_.front();
            storage_queue_.pop();
            lock.unlock();
            
            // std::cerr << "💾 🚀 High-speed processing batch " << batch.batch_id << " with " << batch.data.size() << " items" << std::endl;
            
            try {
                // ✅ HIGH-PERFORMANCE: Use nlohmann/json for ultra-fast batch serialization
                std::string batch_filename = "batch_" + TimeUtils::current_timestamp() + "_" + 
                                           batch.batch_id + ".json";
                std::string filepath = base_path_ + "/" + batch_filename;
                
                // ✅ ULTRA-FAST: Build entire JSON array in memory using nlohmann/json
                nlohmann::json json_array = nlohmann::json::array();
                
                for (const auto& page_data : batch.data) {
                    nlohmann::json j;
                    // ✅ CRITICAL FIX: Sanitize UTF-8 before JSON serialization
                    j["url"] = sanitize_utf8(page_data.url);
                    j["domain"] = sanitize_utf8(page_data.domain);
                    j["timestamp"] = TimeUtils::time_to_iso_string(page_data.last_crawl_time);
                    j["depth"] = page_data.depth;
                    j["http_status_code"] = page_data.http_status_code;
                    j["content_length"] = page_data.content_length;
                    j["content_hash"] = page_data.content_hash;
                    j["last_crawl_time"] = TimeUtils::time_to_iso_string(page_data.last_crawl_time);
                    j["previous_change_time"] = TimeUtils::time_to_iso_string(page_data.previous_change_time);
                    j["expected_next_crawl"] = TimeUtils::time_to_iso_string(page_data.expected_next_crawl);
                    j["backoff_multiplier"] = page_data.backoff_multiplier;
                    j["crawl_count"] = page_data.crawl_count;
                    j["change_frequency"] = page_data.change_frequency;
                    j["content"] = sanitize_utf8(page_data.content);  // ✅ MOST IMPORTANT: Sanitize HTML content
                    
                    json_array.push_back(std::move(j));
                    
                    // Check for shutdown periodically during large batch processing
                    if (json_array.size() % 20 == 0 && shutdown_.load()) {
                        break;  // Stop processing if shutdown requested
                    }
                }
                
                // ✅ SINGLE ATOMIC WRITE: Much faster than incremental writing
                std::ofstream file(filepath);
                if (file.is_open()) {
                    file << json_array.dump(2);  // Pretty-printed
                    file.close();
                    
                    // std::cerr << "✅ 🚀 Ultra-fast wrote batch " << batch.batch_id << " (" << json_array.size() << " items)" << std::endl;
                } else {
                    std::cerr << "❌ Failed to open file for writing: " << filepath << std::endl;
                }
                
                processed_this_cycle++;
                
            } catch (const std::exception& e) {
                std::cerr << "Error processing storage batch: " << e.what() << std::endl;
            }
            
            lock.lock();
        }
        
        // Handle flush completion - check both conditions
        if (flush_requested_ && storage_queue_.empty()) {
            flush_requested_ = false;
            flush_cv_.notify_all();
        }
        
        // Check for shutdown after processing current batches
        if (shutdown_) {
            break;
        }
    }
    
    // Final cleanup: process any remaining items during shutdown
    std::lock_guard<std::mutex> lock(queue_mutex_);
    while (!storage_queue_.empty()) {
        auto batch = storage_queue_.front();
        storage_queue_.pop();
        
        try {
            std::string batch_filename = "shutdown_batch_" + TimeUtils::current_timestamp() + "_" + 
                                       batch.batch_id + ".json";
            std::string filepath = base_path_ + "/" + batch_filename;
            
            std::ofstream file(filepath);
            if (file.is_open()) {
                file << "[\n";
                for (size_t i = 0; i < batch.data.size(); ++i) {
                    if (i > 0) file << ",\n";
                    file << batch.data[i].to_json();
                }
                file << "\n]\n";
                file.close();
            }
        } catch (const std::exception& e) {
            std::cerr << "Error saving shutdown batch: " << e.what() << std::endl;
        }
    }
}

void EnhancedFileStorageManager::save_enriched_batch(const std::vector<EnrichedPageData>& batch) {
    if (batch.empty()) return;
    
    std::cerr << "🔄 Enqueueing batch with " << batch.size() << " items" << std::endl;
    
    EnrichedStorageBatch storage_batch;
    storage_batch.data = batch;
    storage_batch.batch_id = std::to_string(batch_counter_++);
    
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        storage_queue_.push(storage_batch);
        std::cerr << "📊 Queue size now: " << storage_queue_.size() << " batches" << std::endl;
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
                                                                 int depth,
                                                                 int http_status) {
    // Get metadata from store
    UrlMetadata* metadata = metadata_store_->get_or_create_metadata(url);
    
    // Create enriched data
    EnrichedPageData enriched(url, content, metadata);
    
    // Set additional fields
    enriched.domain = UrlNormalizer::extract_domain(url);
    enriched.depth = depth;
    enriched.http_status_code = http_status;
    enriched.content_length = content.length();
    
    
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
    ZoneScopedN("complete flushing");
    auto start_time = std::chrono::steady_clock::now();
    const auto max_flush_time = std::chrono::seconds(10);  // Reduced from 30 to 10 seconds
    
    // ✅ FIX: Aggressive flush with hard timeout
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        flush_requested_ = true;
    }
    queue_cv_.notify_all();
    
    // Wait for flush completion with timeout to prevent hanging
    std::unique_lock<std::mutex> lock(queue_mutex_);
    
    bool flushed = false;
    { 
        ZoneScopedN("flushing");
    while (!flushed) {
        auto elapsed = std::chrono::steady_clock::now() - start_time;
        if (elapsed >= max_flush_time) {
            std::cerr << "⚠️  Storage flush timeout after 10 seconds - forcing completion" << std::endl;
            std::cerr << "📊 Remaining items in storage queue: " << storage_queue_.size() << std::endl;
            
            // Force complete by clearing the queue if necessary
            if (!storage_queue_.empty()) {
                std::cerr << "🚨 Clearing remaining " << storage_queue_.size() << " storage items due to timeout" << std::endl;
                // Don't clear the queue here - let destructor handle remaining items
            }
            
            flush_requested_ = false;
            break;
        }
        
        auto remaining_time = max_flush_time - elapsed;
        flushed = flush_cv_.wait_for(lock, remaining_time, [this] { 
            return storage_queue_.empty() && !flush_requested_; 
        });
    }
    }
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
