# High-Performance Web Crawler

A production-ready, multi-threaded web crawler written in C++ designed to power AI-based search engines. Built for speed, scalability, and reliability.

## 🚀 Features

### Core Capabilities
- **High-Performance Multi-Threading**: Optimized for 50-100+ pages/sec on modern hardware
- **Intelligent URL Prioritization**: Priority queue system favoring high-quality domains
- **Robust Rate Limiting**: Per-domain politeness with exponential backoff
- **Comprehensive robots.txt Support**: Full compliance with robots.txt standards
- **Advanced URL Normalization**: Handles relative URLs, removes tracking parameters
- **Content Quality Filtering**: Intelligent filtering of low-value content
- **Graceful Error Handling**: Retry logic with exponential backoff

### Storage & Metadata
- **Structured Metadata Storage**: SQLite database for crawl metadata
- **Batch File Operations**: Optimized I/O with configurable batch sizes
- **CSV Logging**: Human-readable crawl logs
- **Base64 Content Encoding**: Safe storage of HTML content

### Performance Optimizations
- **Connection Pooling**: Reusable HTTP connections for better performance
- **Memory Management**: Efficient bloom filters and queue management
- **Adaptive Batching**: Dynamic batch sizes based on queue status
- **Thread-Local Caching**: Reduced lock contention

## 📋 Requirements

### System Dependencies
- **CMake** >= 3.10
- **C++17** compatible compiler (GCC 7+, Clang 5+)
- **libcurl** development headers
- **libgumbo** HTML parser
- **SQLite3** development headers
- **pkg-config**

### Hardware Recommendations
- **CPU**: 4+ cores (scales with core count)
- **RAM**: 8GB+ (depends on queue size and thread count)
- **Storage**: SSD recommended for better I/O performance
- **Network**: High-bandwidth connection for optimal crawling

## 🛠 Installation

### Quick Start (Ubuntu/Debian)
```bash
# Install dependencies and build
cd crawler
chmod +x scripts/build.sh
./scripts/build.sh --install-deps

# Run the crawler
./crawler
```

### Manual Installation
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential cmake libcurl4-openssl-dev \
    libgumbo-dev libsqlite3-dev pkg-config

# Build the crawler
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### Build Options
```bash
# Debug build with sanitizers
./scripts/build.sh --debug

# Clean build
./scripts/build.sh --clean

# Install dependencies automatically
./scripts/build.sh --install-deps

# Run tests after build
./scripts/build.sh --tests
```

## 🔧 Configuration

### Command Line Usage
```bash
# Basic usage
./crawler

# Custom parameters
./crawler [max_threads] [max_depth] [max_queue_size]

# Example: 16 threads, depth 5, 100k URL queue
./crawler 16 5 100000
```

### Configuration Files

#### `config/crawler.conf`
Main configuration file with performance and behavior settings:
```ini
[crawler]
max_threads = 16
max_depth = 5
max_queue_size = 100000
default_crawl_delay = 200

[storage]
raw_html_dir = ../../data/raw
metadata_db = ../../data/processed/crawl_metadata.db
batch_size = 50

[performance]
connection_pool_size = 50
bloom_filter_capacity = 2000000
```

#### `config/blacklist.txt`
Domain blacklist for permanently blocked domains:
```
facebook.com
twitter.com
youtube.com
# Add more domains as needed
```

## 📊 Output Structure

### Raw HTML Storage
- **Location**: `data/raw/`
- **Format**: JSON batches with base64-encoded HTML
- **Naming**: `batch_YYYYMMDD_HHMMSS_XXX.json`

### Metadata Database
- **Location**: `data/processed/crawl_metadata.db`
- **Schema**: URL, title, status code, depth, domain, content size, timestamp
- **Indexes**: Optimized for domain and timestamp queries

### CSV Logs
- **Location**: `data/processed/crawl_log.csv`
- **Format**: Human-readable crawl statistics
- **Real-time**: Updated during crawling for monitoring

## 🎯 Performance Tuning

### Thread Configuration
```bash
# Conservative (low resource usage)
./crawler 4 3 50000

# Balanced (recommended)
./crawler 16 5 100000

# Aggressive (high performance)
./crawler 32 7 500000
```

### Memory Usage
- **Base Memory**: ~100MB
- **Per Thread**: ~10-20MB
- **Queue Memory**: ~100 bytes per URL
- **Connection Pool**: ~1KB per connection

### Disk Usage
- **Raw HTML**: Varies by content (typically 10-50KB per page)
- **Metadata DB**: ~1KB per page
- **Logs**: Minimal (~100 bytes per page)

## 🔍 Monitoring

### Real-time Statistics
The crawler displays comprehensive statistics every 30 seconds:
```
================== CRAWLER STATISTICS ==================
Runtime: 300 seconds
Crawl rate: 45.2 pages/sec
Discovery rate: 234.1 links/sec
Download rate: 2.3 MB/sec
Total pages: 13560
Total links: 70230
Network errors: 45
Queue size: 85430
Active threads: 16
========================================================
```

### Performance Metrics
- **Crawl Rate**: Pages successfully processed per second
- **Discovery Rate**: New URLs discovered per second
- **Error Rate**: Network/HTTP errors per second
- **Queue Health**: Current queue size and growth rate

## 🛡 Politeness & Ethics

### Rate Limiting
- **Default Delay**: 200ms between requests per domain
- **Exponential Backoff**: Automatic delay increases on errors
- **Server Throttling**: Respects HTTP 429/503 responses

### robots.txt Compliance
- **Full Support**: Parses and respects robots.txt files
- **Caching**: 24-hour cache to minimize robots.txt requests
- **User Agent**: Clearly identifies crawler with contact info

### Content Filtering
- **Quality Focus**: Prioritizes educational, news, and reference content
- **Spam Avoidance**: Filters out low-quality and duplicate content
- **Blacklisting**: Permanent and temporary domain blocking

## 🐛 Troubleshooting

### Common Issues

#### Build Failures
```bash
# Missing dependencies
./scripts/build.sh --install-deps

# CMake version too old
# Install newer CMake from official sources

# Gumbo library not found
sudo apt-get install libgumbo-dev
```

#### Runtime Issues
```bash
# Permission denied on data directories
mkdir -p data/raw data/processed
chmod 755 data/raw data/processed

# SQLite database locked
# Stop other crawler instances

# Network connectivity issues
# Check firewall and DNS settings
```

#### Performance Issues
```bash
# Low crawl rate
# Reduce thread count or increase timeout values
# Check network bandwidth and latency

# High memory usage
# Reduce max_queue_size parameter
# Lower thread count

# Disk space issues
# Monitor data/raw directory size
# Implement log rotation
```

### Debugging
```bash
# Debug build with verbose output
./scripts/build.sh --debug
./build/crawler

# Check library dependencies
ldd build/crawler

# Monitor system resources
htop
iotop
```

## 🚦 Production Deployment

### System Requirements
- **OS**: Linux (Ubuntu 18.04+, CentOS 7+)
- **Architecture**: x86_64
- **Network**: Stable internet connection
- **Monitoring**: System monitoring tools (htop, iotop, etc.)

### Deployment Checklist
1. ✅ Install system dependencies
2. ✅ Configure firewall (outbound HTTP/HTTPS)
3. ✅ Set up log rotation
4. ✅ Configure monitoring alerts
5. ✅ Test with small queue size first
6. ✅ Monitor resource usage during ramp-up

### Resource Monitoring
```bash
# Monitor CPU and memory usage
watch -n 5 'ps aux | grep crawler'

# Monitor disk I/O
iostat -x 5

# Monitor network usage
iftop

# Check disk space
df -h data/
```

## 🔮 Future Enhancements

### Planned Features
- **Distributed Crawling**: Multi-machine coordination
- **Proxy Rotation**: Automatic proxy management
- **Content Deduplication**: Advanced duplicate detection
- **Machine Learning**: AI-driven URL prioritization
- **Real-time Analytics**: Web dashboard for monitoring
- **API Integration**: RESTful API for crawler control

### Optimization Opportunities
- **GPU Acceleration**: CUDA-based HTML parsing
- **Memory Mapping**: Faster file I/O
- **Compression**: Real-time content compression
- **Caching**: Redis-based URL caching

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review configuration examples

---

**Note**: This crawler is designed for legitimate research and indexing purposes. Please respect website terms of service and robots.txt files. Use responsibly and in compliance with applicable laws and regulations.
