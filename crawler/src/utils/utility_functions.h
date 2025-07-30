#pragma once

#include <string>
#include <ctime>
#include <chrono>

// Utility functions
std::string base64_encode(const std::string& in);
std::string get_timestamp_string();
std::string sanitize_filename(const std::string& input);

// Date parsing functions
std::chrono::system_clock::time_point parse_rfc2822_date(const std::string& date_str);
std::chrono::system_clock::time_point parse_iso8601_date(const std::string& date_str);
