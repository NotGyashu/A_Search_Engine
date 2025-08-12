#ifndef GDRIVE_MOUNT_STORAGE_H
#define GDRIVE_MOUNT_STORAGE_H

#include "enriched_storage.h"
#include "gdrive_mount_manager.h"
#include <memory>
#include <string>
#include <atomic>

namespace CrawlScheduling {

/**
 * Mount-Aware Storage Manager
 * Uses Google Drive mount for direct filesystem writes
 * Falls back to local storage if mount is unavailable
 */
class GDriveMountStorage {
public:
    /**
     * Constructor
     * @param mount_manager Shared mount manager instance
     * @param metadata_store Metadata store for enriched data
     * @param mode Crawler mode (REGULAR or FRESH)
     */
    GDriveMountStorage(std::shared_ptr<GDriveMountManager> mount_manager,
                       std::shared_ptr<CrawlMetadataStore> metadata_store,
                       const std::string& mode);
    
    ~GDriveMountStorage();

    /**
     * Save enriched batch to mounted Google Drive
     * @param batch Vector of enriched page data
     */
    void save_enriched_batch(const std::vector<EnrichedPageData>& batch);

    /**
     * Save HTML batch with metadata to mounted Google Drive
     * @param simple_batch Vector of URL-content pairs
     */
    void save_html_batch_with_metadata(
        const std::vector<std::pair<std::string, std::string>>& simple_batch);

    /**
     * Flush all pending operations
     */
    void flush();

    /**
     * Get storage statistics
     */
    struct Stats {
        size_t files_written_to_mount = 0;
        size_t files_written_to_local = 0;
        size_t mount_write_failures = 0;
        size_t total_bytes_written = 0;
        std::string current_storage_path;
        bool using_mount = false;
    };
    Stats get_stats() const;

private:
    std::shared_ptr<GDriveMountManager> mount_manager_;
    std::unique_ptr<EnhancedFileStorageManager> mount_storage_;
    std::unique_ptr<EnhancedFileStorageManager> fallback_storage_;
    std::string mode_;
    
    // Statistics
    mutable std::mutex stats_mutex_;
    Stats stats_;
    
    // Internal methods
    std::string get_storage_path();
    bool is_mount_available();
    EnhancedFileStorageManager* get_active_storage();
    void update_stats(bool used_mount, size_t bytes_written, bool success);
};

} // namespace CrawlScheduling

#endif // GDRIVE_MOUNT_STORAGE_H
