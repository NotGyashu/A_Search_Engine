#include "gdrive_mount_manager.h"
#include <filesystem>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <cstdlib>
#include <unistd.h>
#include <sys/wait.h>
#include <signal.h>
#include <fstream>
#include <mutex>
#include <thread>
#include <chrono>

GDriveMountManager::GDriveMountManager(const std::string& rclone_remote, 
                                       const std::string& remote_path,
                                       const std::string& mount_point)
    : rclone_remote_(rclone_remote), 
      remote_path_(remote_path),
      mount_point_(mount_point) {
}

GDriveMountManager::~GDriveMountManager() {
    shutdown();
}

void GDriveMountManager::cleanup_existing_mount(const std::string& mount_point) {
    std::cout << "🧹 Static cleanup: Skipping cleanup for permanent mount at " << mount_point << std::endl;
    std::cout << "ℹ️  Using persistent systemd-managed mount" << std::endl;
}

bool GDriveMountManager::initialize() {
    std::cout << "🔄 Initializing Google Drive mount manager..." << std::endl;
    std::cout << "📱 Using persistent systemd-managed mount" << std::endl;
    
    // Step 1: Verify mount point exists and is accessible
    if (!std::filesystem::exists(mount_point_) || !std::filesystem::is_directory(mount_point_)) {
        std::cerr << "❌ Mount point does not exist or is not accessible: " << mount_point_ << std::endl;
        return false;
    }
    
    // Step 2: Verify mount is working
    std::cout << "🔍 Verifying persistent mount..." << std::endl;
    if (!verify_mount()) {
        std::cerr << "❌ Mount verification failed - persistent mount may not be working" << std::endl;
        return false;
    }
    
    // Step 3: Create required directory structure
    try {
        std::string daily_path = get_daily_path(get_current_date_string());
        std::string live_path = get_live_path();
        
        std::filesystem::create_directories(daily_path);
        std::filesystem::create_directories(live_path);
        
        std::cout << "📁 Verified/created mounted directories:" << std::endl;
        std::cout << "   - Daily: " << daily_path << std::endl;
        std::cout << "   - Live: " << live_path << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Failed to create directory structure: " << e.what() << std::endl;
        return false;
    }
    
    // Step 4: Start health monitoring
    health_monitor_thread_ = std::thread(&GDriveMountManager::health_monitor_worker, this);
    
    is_mounted_ = true;
    is_healthy_ = true;
    
    std::cout << "✅ Google Drive mount manager initialized successfully" << std::endl;
    std::cout << "   📍 Mount point: " << mount_point_ << std::endl;
    std::cout << "   🔗 Persistent systemd mount" << std::endl;
    
    return true;
}

bool GDriveMountManager::verify_mount() {
    // Check if mount point exists and is a directory
    if (!std::filesystem::exists(mount_point_) || !std::filesystem::is_directory(mount_point_)) {
        return false;
    }
    
    // Try to write a test file to verify write access with timeout handling
    std::string test_file = mount_point_ + "/.mount_test_" + std::to_string(getpid());
    
    try {
        // First, try a simple directory listing to check for I/O errors
        try {
            auto directory_iter = std::filesystem::directory_iterator(mount_point_);
            // Just attempt to create the iterator - if mount is stale, this will throw
        } catch (const std::filesystem::filesystem_error& e) {
            std::string error_msg = e.what();
            if (error_msg.find("Input/output error") != std::string::npos ||
                error_msg.find("Transport endpoint is not connected") != std::string::npos ||
                error_msg.find("Device or resource busy") != std::string::npos) {
                
                std::cerr << "⚠️  Mount I/O error detected: " << error_msg << std::endl;
                is_healthy_ = false;
                
                std::lock_guard<std::mutex> lock(stats_mutex_);
                stats_.is_healthy = false;
                stats_.last_error = "Mount I/O error: " + error_msg;
                
                return false;
            }
            throw; // Re-throw if it's a different error
        }
        
        std::ofstream test(test_file);
        if (!test.is_open()) {
            return false;
        }
        
        test << "Mount test - " << std::time(nullptr) << std::endl;
        test.close();
        
        // Try to read it back
        std::ifstream read_test(test_file);
        if (!read_test.is_open()) {
            return false;
        }
        
        std::string content;
        std::getline(read_test, content);
        read_test.close();
        
        // Clean up test file
        std::filesystem::remove(test_file);
        
        // Update health status
        is_healthy_ = true;
        
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.is_healthy = true;
        stats_.last_health_check = std::chrono::system_clock::now();
        stats_.health_check_count++;
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Mount health check failed: " << e.what() << std::endl;
        is_healthy_ = false;
        
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.is_healthy = false;
        stats_.last_error = e.what();
        
        return false;
    }
}

std::string GDriveMountManager::get_daily_path(const std::string& date_string) {
    return mount_point_ + "/daily/" + date_string;
}

std::string GDriveMountManager::get_live_path() {
    return mount_point_ + "/live";
}

GDriveMountManager::Stats GDriveMountManager::get_stats() const {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    Stats current_stats = stats_;
    current_stats.is_mounted = is_mounted_.load();
    current_stats.is_healthy = is_healthy_.load();
    return current_stats;
}

void GDriveMountManager::shutdown() {
    std::cout << "🔄 Shutting down Google Drive mount manager..." << std::endl;
    
    // Signal shutdown
    shutdown_requested_ = true;
    
    // Stop health monitor - with timeout mechanism via the shutdown loop
    if (health_monitor_thread_.joinable()) {
        std::cout << "⏳ Waiting for health monitor to stop..." << std::endl;
        
        // Wait for a reasonable time, the health monitor checks shutdown_requested_ every second
        auto start = std::chrono::steady_clock::now();
        const auto max_wait = std::chrono::seconds(8);  // Give some buffer beyond the 1-second check interval
        
        while (health_monitor_thread_.joinable() && 
               (std::chrono::steady_clock::now() - start) < max_wait) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        
        if (health_monitor_thread_.joinable()) {
            health_monitor_thread_.join();
        }
    }
    
    // Note: Leaving persistent mount intact (managed by systemd)
    std::cout << "ℹ️  Persistent mount remains active (systemd-managed)" << std::endl;
    
    std::cout << "✅ Google Drive mount manager shutdown complete" << std::endl;
}

bool GDriveMountManager::setup_mount_point() {
    try {
        std::cout << "🔍 Setting up mount point: " << mount_point_ << std::endl;
        
        // First, check if there's already a mount at this location
        std::string check_mount_cmd = "mount | grep \"" + mount_point_ + "\"";
        int mount_exists = std::system((check_mount_cmd + " > /dev/null 2>&1").c_str());
        
        if (mount_exists == 0) {
            std::cout << "🧹 Found existing mount, attempting cleanup..." << std::endl;
            
            // Force cleanup of existing mounts
            std::string cleanup_commands[] = {
                "fusermount -u \"" + mount_point_ + "\" 2>/dev/null",
                "sudo umount -f \"" + mount_point_ + "\" 2>/dev/null", 
                "sudo umount -l \"" + mount_point_ + "\" 2>/dev/null",  // lazy unmount
                "pkill -f \"rclone mount.*" + mount_point_ + "\" 2>/dev/null"
            };
            
            for (const auto& cmd : cleanup_commands) {
                std::cout << "   Executing: " << cmd << std::endl;
                std::system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(1000));
            }
            
            // Verify cleanup worked
            int still_mounted = std::system((check_mount_cmd + " > /dev/null 2>&1").c_str());
            if (still_mounted == 0) {
                std::cerr << "⚠️  Warning: Mount still exists after cleanup attempts" << std::endl;
            } else {
                std::cout << "✅ Mount cleanup successful" << std::endl;
            }
        }
        
        // Now check if mount point directory exists and is accessible
        if (std::filesystem::exists(mount_point_)) {
            std::cout << "🔍 Mount point directory exists, checking accessibility..." << std::endl;
            
            // Try to access the mount point to see if it's stale
            try {
                // This will fail with "Transport endpoint is not connected" if it's a stale mount
                std::filesystem::create_directories(mount_point_ + "/.test_dir");
                std::filesystem::remove(mount_point_ + "/.test_dir");
                std::cout << "✅ Mount point is accessible" << std::endl;
            } catch (const std::filesystem::filesystem_error& e) {
                std::string error_msg = e.what();
                if (error_msg.find("Transport endpoint is not connected") != std::string::npos ||
                    error_msg.find("Device or resource busy") != std::string::npos) {
                    
                    std::cout << "🧹 Detected inaccessible mount point, cleaning up..." << std::endl;
                    
                    // Remove and recreate the mount point directory
                    try {
                        std::filesystem::remove_all(mount_point_);
                        std::cout << "   Removed stale mount point directory" << std::endl;
                    } catch (...) {
                        // If we can't remove it, try with sudo
                        std::string rm_cmd = "sudo rm -rf \"" + mount_point_ + "\"";
                        std::cout << "   Trying with sudo: " << rm_cmd << std::endl;
                        std::system(rm_cmd.c_str());
                    }
                    
                    std::this_thread::sleep_for(std::chrono::seconds(1));
                    std::cout << "✅ Mount point cleanup completed" << std::endl;
                } else {
                    throw; // Re-throw if it's a different error
                }
            }
        }
        
        // Create mount point directory if it doesn't exist
        std::cout << "📁 Creating mount point directory..." << std::endl;
        std::filesystem::create_directories(mount_point_);
        
        // Check if we have write permissions
        if (access(mount_point_.c_str(), W_OK) != 0) {
            std::cerr << "❌ No write permission to mount point: " << mount_point_ << std::endl;
            return false;
        }
        
        std::cout << "✅ Mount point setup completed successfully" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Failed to setup mount point: " << e.what() << std::endl;
        return false;
    }
}

// bool GDriveMountManager::start_rclone_mount() {
//     // Build rclone mount command with simplified, reliable options
//     std::ostringstream cmd;
//     cmd << "rclone mount \"" << rclone_remote_ << ":" << remote_path_ << "\" \"" << mount_point_ << "\" "
//         << "--allow-other "
//         << "--daemon "
//         << "--vfs-cache-mode full "
//         << "--vfs-cache-max-size 2G "
//         << "--buffer-size 256M "
//         << "--transfers 4 "
//         << "--checkers 8 "
//         << "--log-level INFO "
//         << "--log-file /tmp/rclone-mount.log";
    
//     std::string command = cmd.str();
//     std::cout << "🚀 Starting rclone mount: " << command << std::endl;
    
//     // Execute mount command
//     int result = std::system(command.c_str());
    
//     if (result != 0) {
//         std::cerr << "❌ rclone mount command failed with exit code: " << result << std::endl;
//         std::cerr << "   Check /tmp/rclone-mount.log for details" << std::endl;
        
//         // Try a fallback with minimal options
//         std::cout << "🔄 Trying fallback mount with minimal options..." << std::endl;
//         std::ostringstream fallback_cmd;
//         fallback_cmd << "rclone mount \"" << rclone_remote_ << ":" << remote_path_ << "\" \"" << mount_point_ << "\" "
//                      << "--daemon "
//                      << "--log-file /tmp/rclone-mount-fallback.log";
        
//         std::string fallback_command = fallback_cmd.str();
//         std::cout << "🚀 Fallback command: " << fallback_command << std::endl;
        
//         int fallback_result = std::system(fallback_command.c_str());
//         if (fallback_result != 0) {
//             std::cerr << "❌ Fallback mount also failed with exit code: " << fallback_result << std::endl;
//             return false;
//         }
        
//         std::cout << "✅ Fallback mount succeeded" << std::endl;
//     }
    
//     // rclone mount runs in daemon mode, so we don't have the PID directly
//     // We'll rely on health checks to monitor the mount
    
//     return true;
// }

// bool GDriveMountManager::stop_rclone_mount() {
//     std::cout << "🔄 Unmounting Google Drive..." << std::endl;
    
//     try {
//         // First, try to kill any rclone processes using this mount point
//         std::string kill_rclone_cmd = "pkill -f \"rclone mount.*" + mount_point_ + "\"";
//         std::cout << "🔪 Killing rclone processes for mount: " << mount_point_ << std::endl;
//         std::system(kill_rclone_cmd.c_str());
        
//         std::this_thread::sleep_for(std::chrono::seconds(2));
        
//         // Check if there's still a mount entry
//         std::string check_mount_cmd = "mount | grep \"" + mount_point_ + "\"";
//         int mount_exists = std::system((check_mount_cmd + " > /dev/null 2>&1").c_str());
        
//         if (mount_exists == 0) {
//             std::cout << "🧹 Mount still exists, attempting unmount..." << std::endl;
            
//             // Try graceful unmount first
//             std::string umount_cmd = "fusermount -u \"" + mount_point_ + "\" 2>/dev/null";
//             int result = std::system(umount_cmd.c_str());
            
//             if (result != 0) {
//                 std::cout << "⚠️  Graceful unmount failed, trying force unmount..." << std::endl;
                
//                 // Try multiple force unmount methods
//                 std::string force_commands[] = {
//                     "sudo umount -f \"" + mount_point_ + "\" 2>/dev/null",
//                     "sudo umount -l \"" + mount_point_ + "\" 2>/dev/null"  // lazy unmount
//                 };
                
//                 for (const auto& cmd : force_commands) {
//                     std::cout << "   Trying: " << cmd << std::endl;
//                     std::system(cmd.c_str());
//                     std::this_thread::sleep_for(std::chrono::milliseconds(1000));
//                 }
//             }
            
//             // Verify unmount worked
//             int still_mounted = std::system((check_mount_cmd + " > /dev/null 2>&1").c_str());
//             if (still_mounted == 0) {
//                 std::cerr << "⚠️  Warning: Mount still exists after unmount attempts" << std::endl;
//             } else {
//                 std::cout << "✅ Mount successfully unmounted" << std::endl;
//             }
//         } else {
//             std::cout << "ℹ️  No mount found for " << mount_point_ << std::endl;
//         }
        
//         // Force kill any remaining rclone processes (broader search)
//         std::cout << "🔪 Final cleanup: Killing any remaining rclone processes..." << std::endl;
//         std::system("pkill -9 -f rclone 2>/dev/null");
        
//         is_mounted_ = false;
//         is_healthy_ = false;
        
//         std::lock_guard<std::mutex> lock(stats_mutex_);
//         stats_.is_mounted = false;
//         stats_.is_healthy = false;
        
//         std::cout << "✅ Google Drive unmount completed" << std::endl;
//         return true;
        
//     } catch (const std::exception& e) {
//         std::cerr << "⚠️  Error during unmount: " << e.what() << std::endl;
//         return false;
//     }
// }

void GDriveMountManager::health_monitor_worker() {
    std::cout << "🔍 Starting mount health monitor" << std::endl;
    
    while (!shutdown_requested_) {
        if (is_mounted_) {
            if (!perform_health_check()) {
                std::cerr << "⚠️  Mount health check failed, attempting recovery..." << std::endl;
                
                if (attempt_recovery()) {
                    std::cout << "✅ Mount recovery successful" << std::endl;
                } else {
                    std::cerr << "❌ Mount recovery failed, will retry in " << RECOVERY_RETRY_SECONDS << " seconds" << std::endl;
                }
            }
        }
        
        // Wait before next health check
        for (int i = 0; i < HEALTH_CHECK_INTERVAL_SECONDS && !shutdown_requested_; ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    
    std::cout << "🔍 Mount health monitor stopped" << std::endl;
}

bool GDriveMountManager::perform_health_check() {
    return verify_mount();
}

bool GDriveMountManager::attempt_recovery() {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    stats_.recovery_count++;
    
    std::cout << "🔧 Attempting mount recovery..." << std::endl;
    
    // For persistent mounts, check if it's a stale mount issue
    std::string check_mount_cmd = "mount | grep \"" + mount_point_ + "\"";
    int mount_exists = std::system((check_mount_cmd + " > /dev/null 2>&1").c_str());
    
    if (mount_exists == 0) {
        std::cout << "📍 Mount entry exists, checking if it's stale..." << std::endl;
        
        // Try to detect and fix stale mounts
        try {
            auto directory_iter = std::filesystem::directory_iterator(mount_point_);
            // If we can list the directory, mount might be recovering
            std::this_thread::sleep_for(std::chrono::seconds(3));
            
        } catch (const std::filesystem::filesystem_error& e) {
            std::string error_msg = e.what();
            if (error_msg.find("Input/output error") != std::string::npos ||
                error_msg.find("Transport endpoint is not connected") != std::string::npos) {
                
                std::cout << "🔄 Detected stale mount, attempting recovery..." << std::endl;
                
                // Try to remount by unmounting and letting systemd restart
                std::vector<std::string> recovery_commands = {
                    "fusermount -u \"" + mount_point_ + "\" 2>/dev/null || true",
                    "sudo umount -l \"" + mount_point_ + "\" 2>/dev/null || true",
                    "systemctl restart rclone-gdrive-mount.service 2>/dev/null || true"
                };
                
                for (const auto& cmd : recovery_commands) {
                    std::cout << "   Executing: " << cmd << std::endl;
                    std::system(cmd.c_str());
                    std::this_thread::sleep_for(std::chrono::seconds(2));
                }
                
                // Wait a bit longer for systemd to restart the mount
                std::cout << "⏳ Waiting for mount to recover..." << std::endl;
                std::this_thread::sleep_for(std::chrono::seconds(5));
            }
        }
    } else {
        std::cout << "❌ No mount entry found, mount may have been disconnected" << std::endl;
    }
    
    // Give more time for the mount to stabilize
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    if (verify_mount()) {
        is_mounted_ = true;
        is_healthy_ = true;
        std::cout << "✅ Mount recovery successful" << std::endl;
        return true;
    }
    
    std::cerr << "❌ Mount recovery failed - mount may be temporarily unavailable" << std::endl;
    return false;
}

std::string GDriveMountManager::get_current_date_string() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto tm = *std::localtime(&time_t);
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d");
    return oss.str();
}

bool GDriveMountManager::is_process_running(pid_t pid) {
    if (pid <= 0) return false;
    return kill(pid, 0) == 0;
}
