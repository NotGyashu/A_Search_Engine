#!/bin/bash

# Standardized Build Script for Mini Search Engine Crawler
# Creates executables in build/ directory and stores data in main data/ directory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Mini Search Engine Crawler Build Script ===${NC}"

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRAWLER_ROOT="$(dirname "$SCRIPT_DIR")"
SEARCH_ENGINE_ROOT="$(dirname "$CRAWLER_ROOT")"
BUILD_DIR="$CRAWLER_ROOT/build"
DATA_DIR="$SEARCH_ENGINE_ROOT/data"

echo -e "${YELLOW}Crawler root: $CRAWLER_ROOT${NC}"
echo -e "${YELLOW}Search engine root: $SEARCH_ENGINE_ROOT${NC}"
echo -e "${YELLOW}Build directory: $BUILD_DIR${NC}"
echo -e "${YELLOW}Data directory: $DATA_DIR${NC}"

# Parse command line arguments
BUILD_TYPE="Release"
CLEAN_BUILD=false
INSTALL_DEPS=false
RUN_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --install-deps)
            INSTALL_DEPS=true
            shift
            ;;
        --tests)
            RUN_TESTS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --debug       Build in debug mode"
            echo "  --clean       Clean build directory first"
            echo "  --install-deps Install system dependencies"
            echo "  --tests       Run tests after build"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install dependencies
install_dependencies() {
    echo -e "${BLUE}Installing system dependencies...${NC}"
    
    if command_exists apt-get; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y \
            build-essential \
            cmake \
            libcurl4-openssl-dev \
            libgumbo-dev \
            libsqlite3-dev \
            pkg-config \
            git \
            ninja-build
    elif command_exists yum; then
        # RHEL/CentOS
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y \
            cmake \
            libcurl-devel \
            gumbo-parser-devel \
            sqlite-devel \
            pkgconfig \
            git \
            ninja-build
    elif command_exists brew; then
        # macOS
        brew install \
            cmake \
            curl \
            gumbo-parser \
            sqlite3 \
            pkg-config \
            ninja
    else
        echo -e "${RED}Unsupported package manager. Please install dependencies manually:${NC}"
        echo "  - CMake (>= 3.10)"
        echo "  - libcurl development headers"
        echo "  - Gumbo HTML parser development headers"
        echo "  - SQLite3 development headers"
        echo "  - pkg-config"
        exit 1
    fi
    
    echo -e "${GREEN}Dependencies installed successfully${NC}"
}

# Install dependencies if requested
if [[ "$INSTALL_DEPS" == true ]]; then
    install_dependencies
fi

# Check for required tools
echo -e "${BLUE}Checking build requirements...${NC}"

if ! command_exists cmake; then
    echo -e "${RED}CMake not found. Please install CMake >= 3.10${NC}"
    exit 1
fi

if ! command_exists pkg-config; then
    echo -e "${RED}pkg-config not found. Please install pkg-config${NC}"
    exit 1
fi

# Check CMake version
CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
CMAKE_MAJOR=$(echo $CMAKE_VERSION | cut -d'.' -f1)
CMAKE_MINOR=$(echo $CMAKE_VERSION | cut -d'.' -f2)

if [[ $CMAKE_MAJOR -lt 3 ]] || [[ $CMAKE_MAJOR -eq 3 && $CMAKE_MINOR -lt 10 ]]; then
    echo -e "${RED}CMake version $CMAKE_VERSION is too old. Please install CMake >= 3.10${NC}"
    exit 1
fi

echo -e "${GREEN}Build requirements satisfied${NC}"

# Create build directory
BUILD_DIR="$CRAWLER_ROOT/build"

if [[ "$CLEAN_BUILD" == true ]] && [[ -d "$BUILD_DIR" ]]; then
    echo -e "${YELLOW}Cleaning build directory...${NC}"
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Create necessary data directories
echo -e "${BLUE}Creating data directories...${NC}"
mkdir -p "$SEARCH_ENGINE_ROOT/data/raw"
mkdir -p "$SEARCH_ENGINE_ROOT/data/processed"
mkdir -p "$SEARCH_ENGINE_ROOT/config"

# Configure build
echo -e "${BLUE}Configuring build ($BUILD_TYPE)...${NC}"

CMAKE_ARGS="-DCMAKE_BUILD_TYPE=$BUILD_TYPE"

# Use Ninja if available for faster builds
if command_exists ninja; then
    CMAKE_ARGS="$CMAKE_ARGS -GNinja"
    BUILDER="ninja"
else
    BUILDER="make"
fi

# Add additional optimizations for release builds
if [[ "$BUILD_TYPE" == "Release" ]]; then
    CMAKE_ARGS="$CMAKE_ARGS -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON"
fi

cmake "$CRAWLER_ROOT" $CMAKE_ARGS

if [[ $? -ne 0 ]]; then
    echo -e "${RED}CMake configuration failed${NC}"
    exit 1
fi

# Build
echo -e "${BLUE}Building crawler...${NC}"
$BUILDER

if [[ $? -ne 0 ]]; then
    echo -e "${RED}Build failed${NC}"
    exit 1
fi

echo -e "${GREEN}Build completed successfully${NC}"

# Check if executable was created
CRAWLER_BINARY="$BUILD_DIR/crawler"
if [[ ! -f "$CRAWLER_BINARY" ]]; then
    echo -e "${RED}Crawler binary not found at $CRAWLER_BINARY${NC}"
    exit 1
fi

# Make executable
chmod +x "$CRAWLER_BINARY"

echo -e "${GREEN}Crawler binary available at: $CRAWLER_BINARY${NC}"

# Display binary info
echo -e "${BLUE}Binary information:${NC}"
file "$CRAWLER_BINARY"
ls -lh "$CRAWLER_BINARY"

# Run tests if requested
if [[ "$RUN_TESTS" == true ]]; then
    echo -e "${BLUE}Running basic tests...${NC}"
    
    # Test basic help output
    if "$CRAWLER_BINARY" --help 2>/dev/null; then
        echo -e "${GREEN}Help output test passed${NC}"
    else
        echo -e "${YELLOW}Help output test failed (not critical)${NC}"
    fi
    
    # Test dependencies are linked correctly
    if ldd "$CRAWLER_BINARY" >/dev/null 2>&1; then
        echo -e "${GREEN}Library linking test passed${NC}"
    else
        echo -e "${RED}Library linking test failed${NC}"
        exit 1
    fi
fi

# Display usage information
echo -e "${BLUE}=== BUILD COMPLETE ===${NC}"
echo -e "${GREEN}To run the crawler:${NC}"
echo -e "  cd $BUILD_DIR && ./crawler"
echo ""
echo -e "${GREEN}Command line options:${NC}"
echo -e "  ./crawler [max_threads] [max_depth] [max_queue_size]"
echo -e "  Example: ./crawler 16 5 100000"
echo ""
echo -e "${GREEN}Configuration files:${NC}"
echo -e "  - Config: $SEARCH_ENGINE_ROOT/crawler/config/crawler.conf"
echo -e "  - Blacklist: $SEARCH_ENGINE_ROOT/crawler/config/blacklist.txt"
echo ""
echo -e "${GREEN}Output directories:${NC}"
echo -e "  - Raw HTML: $SEARCH_ENGINE_ROOT/data/raw/"
echo -e "  - Processed data: $SEARCH_ENGINE_ROOT/data/processed/"
echo ""
echo -e "${YELLOW}Note: Ensure you have sufficient disk space and network bandwidth${NC}"
echo -e "${YELLOW}The crawler can generate significant traffic and data${NC}"