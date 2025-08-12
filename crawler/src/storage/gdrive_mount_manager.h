#ifndef GDRIVE_MOUNT_MANAGER_H
#define GDRIVE_MOUNT_MANAGER_H

#include <string>
#include <atomic>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <chrono>
#include <memory>

/**
 * Google Drive Mount Manager
 * Manages rclone mount for direct filesystem access to Google Drive
 * Replaces the slow sync-based approach with real-time mounted filesystem
 */
class GDriveMountManager {
public:
    /**
     * Constructor
     * @param rclone_remote The rclone remote name (e.g., "rclone-gdrive")
     * @param remote_path The remote path on Google Drive (e.g., "RawHTML")
     * @param mount_point Local mount point (e.g., "/mnt/gdrive-crawler")
     */
    GDriveMountManager(const std::string& rclone_remote, 
                       const std::string& remote_path,
                       const std::string& mount_point);
    
    ~GDriveMountManager();

    /**
     * Static method to cleanup any existing mounts at the given mount point
     * Should be called before creating a new GDriveMountManager instance
     * @param mount_point The mount point to clean up
     */
    static void cleanup_existing_mount(const std::string& mount_point);

    /**
     * Initialize and setup the mount
     * @return true if mount was successfully created
     */
    bool initialize();

    /**
     * Verify mount is active and writable
     * @return true if mount is healthy
     */
    bool verify_mount();

    /**
     * Get the daily archive path for a given date
     * @param date_string Date in YYYY-MM-DD format
     * @return Full path to daily directory
     */
    std::string get_daily_path(const std::string& date_string);

    /**
     * Get the live workspace path
     * @return Full path to live directory
     */
    std::string get_live_path();

    /**
     * Get mount statistics
     */
    struct Stats {
        bool is_mounted = false;
        bool is_healthy = false;
        size_t health_check_count = 0;
        size_t recovery_count = 0;
        std::chrono::system_clock::time_point last_health_check;
        std::string last_error;
    };
    Stats get_stats() const;

    /**
     * Graceful shutdown and cleanup
     */
    void shutdown();

private:
    // Configuration
    std::string rclone_remote_;
    std::string remote_path_;
    std::string mount_point_;
    
    // Mount state
    std::atomic<bool> is_mounted_{false};
    std::atomic<bool> is_healthy_{false};
    std::atomic<bool> shutdown_requested_{false};
    pid_t rclone_process_id_{-1};
    
    // Health monitoring
    std::thread health_monitor_thread_;
    mutable std::mutex stats_mutex_;
    Stats stats_;
    
    // Internal methods
    bool setup_mount_point();
    bool start_rclone_mount();
    bool stop_rclone_mount();
    void health_monitor_worker();
    bool perform_health_check();
    bool attempt_recovery();
    std::string get_current_date_string();
    bool is_process_running(pid_t pid);
    
    // Constants
    static constexpr int HEALTH_CHECK_INTERVAL_SECONDS = 30;
    static constexpr int MOUNT_STARTUP_WAIT_SECONDS = 5;
    static constexpr int RECOVERY_RETRY_SECONDS = 60;
};

#endif // GDRIVE_MOUNT_MANAGER_H
