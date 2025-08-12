#include "gdrive_mount_storage.h"
#include "constants.h"
#include "time_utils.h"
#include <iostream>
#include <filesystem>

namespace CrawlScheduling {

GDriveMountStorage::GDriveMountStorage(std::shared_ptr<GDriveMountManager> mount_manager,
                                       std::shared_ptr<CrawlMetadataStore> metadata_store,
                                       const std::string& mode)
    : mount_manager_(mount_manager), mode_(mode) {
    
    // Initialize mount storage (primary)
    std::string mount_path = get_storage_path();
    mount_storage_ = std::make_unique<EnhancedFileStorageManager>(mount_path, metadata_store);
    
    // Initialize fallback storage (local)
    std::string fallback_path = std::string(CrawlerConstants::Paths::RAW_DATA_PATH);
    if (mode == "REGULAR") {
        fallback_path += "/" + TimeUtils::current_date_string();
    } else {
        fallback_path += "/Live";
    }
    fallback_storage_ = std::make_unique<EnhancedFileStorageManager>(fallback_path, metadata_store);
    
    // Initialize stats
    {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.current_storage_path = mount_path;
        stats_.using_mount = is_mount_available();
    }
    
    std::cout << "📦 Mount-aware storage initialized:" << std::endl;
    std::cout << "   🎯 Primary (mount): " << mount_path << std::endl;
    std::cout << "   🔄 Fallback (local): " << fallback_path << std::endl;
    std::cout << "   ✅ Mount available: " << (stats_.using_mount ? "YES" : "NO") << std::endl;
}

GDriveMountStorage::~GDriveMountStorage() {
    flush();
}

void GDriveMountStorage::save_enriched_batch(const std::vector<EnrichedPageData>& batch) {
    if (batch.empty()) return;
    
    // Calculate approximate batch size for stats
    size_t estimated_bytes = 0;
    for (const auto& page : batch) {
        estimated_bytes += page.url.length() + page.content.length() + 500; // Rough estimate
    }
    
    EnhancedFileStorageManager* storage = get_active_storage();
    bool using_mount = (storage == mount_storage_.get());
    
    try {
        storage->save_enriched_batch(batch);
        update_stats(using_mount, estimated_bytes, true);
        
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Storage write failed: " << e.what() << std::endl;
        update_stats(using_mount, 0, false);
        
        // If mount failed, try fallback
        if (using_mount) {
            std::cerr << "🔄 Retrying with fallback storage..." << std::endl;
            try {
                fallback_storage_->save_enriched_batch(batch);
                update_stats(false, estimated_bytes, true);
            } catch (const std::exception& fallback_error) {
                std::cerr << "❌ Fallback storage also failed: " << fallback_error.what() << std::endl;
                update_stats(false, 0, false);
            }
        }
    }
}

void GDriveMountStorage::save_html_batch_with_metadata(
    const std::vector<std::pair<std::string, std::string>>& simple_batch) {
    
    if (simple_batch.empty()) return;
    
    // Calculate approximate batch size for stats
    size_t estimated_bytes = 0;
    for (const auto& [url, content] : simple_batch) {
        estimated_bytes += url.length() + content.length() + 500; // Rough estimate
    }
    
    EnhancedFileStorageManager* storage = get_active_storage();
    bool using_mount = (storage == mount_storage_.get());
    
    try {
        storage->save_html_batch_with_metadata(simple_batch);
        update_stats(using_mount, estimated_bytes, true);
        
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Storage write failed: " << e.what() << std::endl;
        update_stats(using_mount, 0, false);
        
        // If mount failed, try fallback
        if (using_mount) {
            std::cerr << "🔄 Retrying with fallback storage..." << std::endl;
            try {
                fallback_storage_->save_html_batch_with_metadata(simple_batch);
                update_stats(false, estimated_bytes, true);
            } catch (const std::exception& fallback_error) {
                std::cerr << "❌ Fallback storage also failed: " << fallback_error.what() << std::endl;
                update_stats(false, 0, false);
            }
        }
    }
}

void GDriveMountStorage::flush() {
    if (mount_storage_) {
        mount_storage_->flush();
    }
    if (fallback_storage_) {
        fallback_storage_->flush();
    }
}

GDriveMountStorage::Stats GDriveMountStorage::get_stats() const {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    return stats_;
}

std::string GDriveMountStorage::get_storage_path() {
    if (mode_ == "REGULAR") {
        return mount_manager_->get_daily_path(TimeUtils::current_date_string());
    } else {
        return mount_manager_->get_live_path();
    }
}

bool GDriveMountStorage::is_mount_available() {
    if (!mount_manager_) return false;
    
    // During shutdown or when there are ongoing mount issues, be more conservative
    try {
        bool mount_ok = mount_manager_->verify_mount();
        
        // If mount verification fails, don't immediately retry during heavy I/O
        // This prevents mount thrashing during shutdown
        if (!mount_ok) {
            std::cerr << "⚠️  Mount verification failed, will use fallback storage" << std::endl;
        }
        
        return mount_ok;
        
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Mount availability check failed: " << e.what() << std::endl;
        return false;
    }
}

EnhancedFileStorageManager* GDriveMountStorage::get_active_storage() {
    bool mount_ok = is_mount_available();
    
    // Update stats with current status
    {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.using_mount = mount_ok;
        if (mount_ok) {
            stats_.current_storage_path = get_storage_path();
        } else {
            // Update to fallback path
            std::string fallback_path = std::string(CrawlerConstants::Paths::RAW_DATA_PATH);
            if (mode_ == "REGULAR") {
                fallback_path += "/" + TimeUtils::current_date_string();
            } else {
                fallback_path += "/Live";
            }
            stats_.current_storage_path = fallback_path;
        }
    }
    
    if (mount_ok) {
        return mount_storage_.get();
    } else {
        std::cerr << "⚠️  Mount unavailable, using fallback local storage" << std::endl;
        return fallback_storage_.get();
    }
}

void GDriveMountStorage::update_stats(bool used_mount, size_t bytes_written, bool success) {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    
    if (success) {
        if (used_mount) {
            stats_.files_written_to_mount++;
        } else {
            stats_.files_written_to_local++;
        }
        stats_.total_bytes_written += bytes_written;
    } else {
        if (used_mount) {
            stats_.mount_write_failures++;
        }
    }
}

} // namespace CrawlScheduling
