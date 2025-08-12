#include "html_document.h"
#include "ultra_parser.h"
#include <algorithm>
#include <sstream>
#include <unordered_set>
#include <iterator>
#include <cctype>

HtmlDocument::HtmlDocument(const std::string& html_content) : html_content_(html_content) {
}

// === FAST UTILITY FUNCTIONS (NO REGEX) ===
size_t HtmlDocument::find_case_insensitive(std::string_view haystack, std::string_view needle, size_t start) {
    if (needle.empty() || haystack.size() < needle.size() || start > haystack.size())
        return std::string_view::npos;

    auto to_lower = [](char c) {
        return (c >= 'A' && c <= 'Z') ? (c + 32) : c;
    };

    for (size_t i = start; i <= haystack.size() - needle.size(); ++i) {
        bool match = true;
        for (size_t j = 0; j < needle.size(); ++j) {
            if (to_lower(haystack[i + j]) != to_lower(needle[j])) {
                match = false;
                break;
            }
        }
        if (match) return i;
    }
    return std::string_view::npos;
}



bool HtmlDocument::isValidHtml(const std::string& content) {
    if (content.length() < 20) return false;
    
    std::string_view html(content.substr(0, std::min(content.size(), size_t(1000))));
    return find_case_insensitive(html, "<html") != std::string_view::npos ||
           find_case_insensitive(html, "<!doctype html") != std::string_view::npos ||
           find_case_insensitive(html, "<head") != std::string_view::npos ||
           find_case_insensitive(html, "<body") != std::string_view::npos;
}