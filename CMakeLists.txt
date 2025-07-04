cmake_minimum_required(VERSION 3.10)
project(mini_search_engine)

# Dependencies
find_package(CURL REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GUMBO REQUIRED gumbo)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(
    ${PROJECT_SOURCE_DIR}/third_party/concurrentqueue
    ${GUMBO_INCLUDE_DIRS}
)

# Executable
add_executable(crawler 
    src/crawler.cpp 
    src/utils.cpp
)

# Linking
target_link_libraries(crawler 
    ${CURL_LIBRARIES} 
    pthread
    ${GUMBO_LDFLAGS}
)

# Install third-party deps script
add_custom_target(get_deps 
    COMMAND ./scripts/install_deps.sh
)