#pragma once

#include <string>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <ctime>

/**
 * Centralized time utility functions
 * Provides consistent time formatting and parsing across the crawler
 */
namespace TimeUtils {

/**
 * Convert system_clock time to ISO 8601 string
 * Format: YYYY-MM-DDTHH:MM:SSZ (UTC)
 */
inline std::string time_to_iso_string(const std::chrono::system_clock::time_point& time_point) {
    std::time_t time_t_val = std::chrono::system_clock::to_time_t(time_point);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t_val), "%Y-%m-%dT%H:%M:%SZ");
    return ss.str();
}

/**
 * Convert ISO 8601 string to system_clock time
 * Expected format: YYYY-MM-DDTHH:MM:SSZ
 */
inline std::chrono::system_clock::time_point iso_string_to_time(const std::string& iso_string) {
    std::tm tm = {};
    std::istringstream ss(iso_string);
    ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return std::chrono::system_clock::from_time_t(std::mktime(&tm));
}

/**
 * Get current time as ISO 8601 string
 */
inline std::string current_time_iso() {
    return time_to_iso_string(std::chrono::system_clock::now());
}

/**
 * Get current timestamp for logging/filenames
 * Format: YYYYMMDD_HHMMSS
 */
inline std::string current_timestamp() {
    auto now = std::chrono::system_clock::now();
    std::time_t time_t_val = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t_val), "%Y%m%d_%H%M%S");
    return ss.str();
}

/**
 * Format duration for human-readable output
 */
inline std::string format_duration(const std::chrono::milliseconds& duration) {
    auto hours = std::chrono::duration_cast<std::chrono::hours>(duration);
    auto minutes = std::chrono::duration_cast<std::chrono::minutes>(duration % std::chrono::hours(1));
    auto seconds = std::chrono::duration_cast<std::chrono::seconds>(duration % std::chrono::minutes(1));
    auto ms = duration % std::chrono::seconds(1);
    
    std::stringstream ss;
    if (hours.count() > 0) {
        ss << hours.count() << "h ";
    }
    if (minutes.count() > 0) {
        ss << minutes.count() << "m ";
    }
    if (seconds.count() > 0) {
        ss << seconds.count() << "s ";
    }
    if (ms.count() > 0) {
        ss << ms.count() << "ms";
    }
    
    return ss.str();
}

} // namespace TimeUtils
