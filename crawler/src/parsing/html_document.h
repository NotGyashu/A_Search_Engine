#pragma once

#include <string>
#include <string_view>

class HtmlDocument {
public:
    // Constructor
    explicit HtmlDocument(const std::string& html_content);

    // Check if given content is valid HTML
    static bool isValidHtml(const std::string& content);

private:
    std::string html_content_;

    // Utility function to perform case-insensitive search
    static size_t find_case_insensitive(std::string_view haystack, std::string_view needle, size_t start = 0);
};
