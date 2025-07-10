#!/bin/bash

# Standardized Test Script for Mini Search Engine Crawler
# Tests crawler functionality and validates data storage

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Mini Search Engine Crawler Test Suite ===${NC}"

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRAWLER_ROOT="$(dirname "$SCRIPT_DIR")"
SEARCH_ENGINE_ROOT="$(dirname "$CRAWLER_ROOT")"
BUILD_DIR="$CRAWLER_ROOT/build"
DATA_DIR="$SEARCH_ENGINE_ROOT/data"
TEST_OUTPUT_DIR="$SEARCH_ENGINE_ROOT/docs/test_results"

echo -e "${YELLOW}Crawler root: $CRAWLER_ROOT${NC}"
echo -e "${YELLOW}Search engine root: $SEARCH_ENGINE_ROOT${NC}"
echo -e "${YELLOW}Build directory: $BUILD_DIR${NC}"
echo -e "${YELLOW}Data directory: $DATA_DIR${NC}"
echo -e "${YELLOW}Test output directory: $TEST_OUTPUT_DIR${NC}"

# Parse command line arguments
TEST_TYPE="all"
TEST_DURATION=10
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --crawler)
            TEST_TYPE="crawler"
            shift
            ;;
        --duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --crawler           Test only the crawler component"
            echo "  --duration <secs>   Test duration in seconds (default: 10)"
            echo "  --verbose          Enable verbose output"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create test output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Check if build directory exists
if [[ ! -d "$BUILD_DIR" ]]; then
    echo -e "${RED}Error: Build directory not found. Please run build.sh first.${NC}"
    exit 1
fi

# Function to test crawler
test_crawler() {
    echo -e "${BLUE}Testing Crawler Components...${NC}"
    
    # Find crawler executables
    CRAWLER_EXECS=($(find "$BUILD_DIR" -name "*crawler*" -type f -executable))
    
    if [[ ${#CRAWLER_EXECS[@]} -eq 0 ]]; then
        echo -e "${RED}Error: No crawler executables found in $BUILD_DIR${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Found crawler executables:${NC}"
    for exec in "${CRAWLER_EXECS[@]}"; do
        echo -e "  $(basename "$exec")"
    done
    
    # Test each crawler executable
    for exec in "${CRAWLER_EXECS[@]}"; do
        local exec_name=$(basename "$exec")
        echo -e "\n${YELLOW}Testing $exec_name...${NC}"
        
        # Create test log file
        local log_file="$TEST_OUTPUT_DIR/${exec_name}_test.log"
        
        # Run crawler for limited time
        echo -e "Running $exec_name for ${TEST_DURATION} seconds..."
        
        # Start crawler in background
        if [[ "$VERBOSE" == true ]]; then
            timeout ${TEST_DURATION}s "$exec" 4 3 10000 > "$log_file" 2>&1 &
        else
            timeout ${TEST_DURATION}s "$exec" 4 3 10000 > "$log_file" 2>&1 &
        fi
        
        local crawler_pid=$!
        
        # Wait for crawler to finish or timeout
        if wait $crawler_pid 2>/dev/null; then
            echo -e "${GREEN}✅ $exec_name completed successfully${NC}"
        else
            local exit_code=$?
            if [[ $exit_code -eq 124 ]]; then
                echo -e "${GREEN}✅ $exec_name timed out as expected${NC}"
            else
                echo -e "${RED}❌ $exec_name failed with exit code $exit_code${NC}"
                if [[ -f "$log_file" ]]; then
                    echo -e "${YELLOW}Last few lines of log:${NC}"
                    tail -n 10 "$log_file"
                fi
                return 1
            fi
        fi
        
        # Check if log file has reasonable content
        if [[ -f "$log_file" ]]; then
            local log_size=$(stat -c%s "$log_file")
            if [[ $log_size -gt 0 ]]; then
                echo -e "  Log file size: $log_size bytes"
                if [[ "$VERBOSE" == true ]]; then
                    echo -e "${YELLOW}Log content preview:${NC}"
                    head -n 20 "$log_file"
                fi
            else
                echo -e "${YELLOW}Warning: Log file is empty${NC}"
            fi
        fi
    done
    
    echo -e "${GREEN}✅ All crawler tests completed${NC}"
}

# Function to test data directory structure
test_data_structure() {
    echo -e "${BLUE}Testing Data Directory Structure...${NC}"
    
    # Check required directories
    local required_dirs=("raw" "processed" "disk_queue")
    
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$DATA_DIR/$dir" ]]; then
            echo -e "${GREEN}✅ $DATA_DIR/$dir exists${NC}"
        else
            echo -e "${RED}❌ $DATA_DIR/$dir missing${NC}"
            return 1
        fi
    done
    
    # Check data directory permissions
    if [[ -w "$DATA_DIR" ]]; then
        echo -e "${GREEN}✅ Data directory is writable${NC}"
    else
        echo -e "${RED}❌ Data directory is not writable${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Data directory structure test passed${NC}"
}

# Function to validate build outputs
validate_build() {
    echo -e "${BLUE}Validating Build Outputs...${NC}"
    
    # Check if executables exist and are executable
    local exec_count=0
    
    for file in "$BUILD_DIR"/*; do
        if [[ -f "$file" && -x "$file" ]]; then
            echo -e "${GREEN}✅ $(basename "$file") is executable${NC}"
            ((exec_count++))
        fi
    done
    
    if [[ $exec_count -eq 0 ]]; then
        echo -e "${RED}❌ No executable files found in build directory${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Found $exec_count executable(s)${NC}"
    return 0
}

# Function to run performance test
run_performance_test() {
    echo -e "${BLUE}Running Performance Test...${NC}"
    
    # Find the best crawler executable
    local crawler_exec=""
    
    if [[ -f "$BUILD_DIR/crawler" ]]; then
        crawler_exec="$BUILD_DIR/crawler"
    else
        echo -e "${RED}❌ No suitable crawler executable found${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Using $(basename "$crawler_exec") for performance test...${NC}"
    
    # Run performance test
    local perf_log="$TEST_OUTPUT_DIR/performance_test.log"
    local start_time=$(date +%s)
    
    echo -e "Running performance test for ${TEST_DURATION} seconds..."
    timeout ${TEST_DURATION}s "$crawler_exec" 8 3 50000 > "$perf_log" 2>&1 || true
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Extract performance metrics from log
    if [[ -f "$perf_log" ]]; then
        local pages_crawled=$(grep -o "Total pages: [0-9]*" "$perf_log" | tail -1 | grep -o "[0-9]*" || echo "0")
        local links_found=$(grep -o "Total links: [0-9]*" "$perf_log" | tail -1 | grep -o "[0-9]*" || echo "0")
        
        echo -e "${GREEN}Performance Test Results:${NC}"
        echo -e "  Duration: ${duration}s"
        echo -e "  Pages crawled: $pages_crawled"
        echo -e "  Links found: $links_found"
        
        if [[ $pages_crawled -gt 0 ]]; then
            local pages_per_sec=$(echo "scale=2; $pages_crawled / $duration" | bc -l 2>/dev/null || echo "N/A")
            echo -e "  Pages/sec: $pages_per_sec"
        fi
        
        echo -e "${GREEN}✅ Performance test completed${NC}"
    else
        echo -e "${RED}❌ Performance test log not found${NC}"
        return 1
    fi
}

# Main test execution
echo -e "${YELLOW}Starting tests...${NC}"
echo -e "Test type: $TEST_TYPE"
echo -e "Test duration: ${TEST_DURATION}s"
echo -e "Verbose: $VERBOSE"

# Run tests based on type
case $TEST_TYPE in
    "crawler")
        validate_build || exit 1
        test_data_structure || exit 1
        test_crawler || exit 1
        run_performance_test || exit 1
        ;;
    "all")
        validate_build || exit 1
        test_data_structure || exit 1
        test_crawler || exit 1
        run_performance_test || exit 1
        ;;
    *)
        echo -e "${RED}Error: Unknown test type: $TEST_TYPE${NC}"
        exit 1
        ;;
esac

echo -e "\n${BLUE}=== TEST SUITE COMPLETE ===${NC}"
echo -e "${GREEN}✅ All tests passed successfully!${NC}"
echo -e "${YELLOW}Test outputs saved to: $TEST_OUTPUT_DIR${NC}"

# Show summary
echo -e "\n${BLUE}Test Summary:${NC}"
if [[ -d "$TEST_OUTPUT_DIR" ]]; then
    echo -e "Test log files:"
    ls -la "$TEST_OUTPUT_DIR"/ | grep -v "^total" | grep -v "^d"
else
    echo -e "${RED}Test output directory not found${NC}"
fi
