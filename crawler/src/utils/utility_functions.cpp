#include "utility_functions.h"
#include <chrono>
#include <sstream>
#include <iomanip>
#include <algorithm>

std::string base64_encode(const std::string& in) {
    static const char* base64_chars =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789+/";
    
    std::string out;
    int val = 0, valb = -6;
    for (unsigned char c : in) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            out.push_back(base64_chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) out.push_back(base64_chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (out.size() % 4) out.push_back('=');
    return out;
}


std::string sanitize_filename(const std::string& input) {
    std::string result = input;
    // Replace invalid characters with underscores
    const std::string invalid_chars = "<>:\"/\\|?*";
    for (char& c : result) {
        if (invalid_chars.find(c) != std::string::npos || c < 32) {
            c = '_';
        }
    }
    
    // Limit length
    if (result.length() > 100) {
        result = result.substr(0, 100);
    }
    
    return result;
}

std::chrono::system_clock::time_point parse_rfc2822_date(const std::string& date_str) {
    // Simplified RFC2822 parser
    // Expected format: "Fri, 16 Dec 2023 08:30:00 GMT"
    std::tm tm = {};
    
    // Try to parse the date string
    std::istringstream ss(date_str);
    ss >> std::get_time(&tm, "%a, %d %b %Y %H:%M:%S");
    
    if (ss.fail()) {
        // Fallback to current time
        return std::chrono::system_clock::now();
    }
    
    std::time_t time = std::mktime(&tm);
    return std::chrono::system_clock::from_time_t(time);
}

std::chrono::system_clock::time_point parse_iso8601_date(const std::string& date_str) {
    // Simplified ISO8601 parser
    // Expected format: "2023-12-16T08:30:00Z"
    std::tm tm = {};
    
    // Try to parse the date string
    std::istringstream ss(date_str);
    ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%S");
    
    if (ss.fail()) {
        // Fallback to current time
        return std::chrono::system_clock::now();
    }
    
    std::time_t time = std::mktime(&tm);
    return std::chrono::system_clock::from_time_t(time);
}
