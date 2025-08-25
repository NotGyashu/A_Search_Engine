# Production-Grade OpenSearch Indexer

A continuous, resource-efficient indexer for OpenSearch designed for 23-hour daily operation with zero data loss and low CPU usage.

## Features

- **Dual-Priority Queue System**: Prioritizes fresh data while processing backlog during idle periods
- **Backpressure Management**: Size-limited queues prevent memory overflow
- **Efficient Bulk Indexing**: Single HTTP requests for optimal network performance
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals properly
- **Robust File Management**: Automatic file movement and error recovery
- **OpenSearch Initialization**: Creates indices, templates, and aliases
- **Comprehensive Logging**: Detailed statistics and error reporting
- **Health Monitoring**: Periodic cluster health checks

## Architecture

### Core Operational Model

The indexer operates in a continuous "watch" mode with strict priority ordering:

1. **Fresh Files Priority**: Scans `toIndex/fresh` directory first
2. **Exclusive Processing**: Processes all fresh files before checking backlog
3. **Backlog Processing**: Processes limited backlog files (5-10) when fresh is empty
4. **Idle Sleep**: Minimal CPU usage when no files to process

### Dual-Queue System

- **High-Priority Queue**: Items from `toIndex/fresh` directory
- **Standard-Priority Queue**: Items from `toIndex/backlog` directory
- **Intelligent Draining**: Always empties high-priority queue first

## Directory Structure

```
toIndex/
├── fresh/          # High-priority files (processed immediately)
├── backlog/        # Standard-priority files (processed when idle)
├── processed/      # Successfully processed files
└── failed/         # Files that failed processing
```

## Installation

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure Environment**:
   - Update `config.py` with your OpenSearch settings
   - Set environment variables or create `.env` file

3. **Initialize Directories**:
```bash
mkdir -p toIndex/{fresh,backlog,processed,failed}
```

## Configuration

Key settings in `config.py`:

### OpenSearch Connection
```python
OPENSEARCH_HOST = "https://localhost:9200"
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = "admin"
OPENSEARCH_AUTH_TYPE = "basic"  # or "aws"
```

### Performance Tuning
```python
BULK_CHUNK_SIZE = 500          # Documents per bulk operation
HIGH_PRIORITY_QUEUE_SIZE = 2000 # High priority queue capacity
STANDARD_PRIORITY_QUEUE_SIZE = 1000 # Standard priority queue capacity
POLL_INTERVAL = 5.0            # Seconds between directory scans
BACKLOG_BATCH_SIZE = 5         # Backlog files per batch
```

### AWS OpenSearch
For AWS OpenSearch, the indexer auto-detects based on hostname:
```python
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "your-access-key"
AWS_SECRET_ACCESS_KEY = "your-secret-key"
```

## Usage

### Starting the Indexer

**Option 1: Direct Python**
```bash
cd indexer
python3 indexer.py
```

**Option 2: Startup Script**
```bash
cd indexer
./start_indexer.sh
```

### Data Format

The indexer expects JSONL files with the following structure:

**Document Entry:**
```json
{
  "type": "document",
  "document_id": "unique_doc_id",
  "url": "https://example.com/page",
  "title": "Page Title",
  "domain": "example.com",
  "description": "Page description",
  "content_type": "article",
  "categories": ["news", "tech"],
  "keywords": ["keyword1", "keyword2"],
  "canonical_url": "https://example.com/canonical",
  "published_date": "2025-01-01",
  "modified_date": "2025-01-02",
  "author_info": {"name": "Author"},
  "structured_data": {...},
  "images": [...],
  "table_of_contents": [...],
  "semantic_info": {...},
  "icons": {...}
}
```

**Chunk Entry:**
```json
{
  "type": "chunk",
  "chunk_id": "unique_chunk_id",
  "document_id": "parent_document_id",
  "text_chunk": "Actual text content...",
  "headings": "[...]",
  "domain_score": 0.8,
  "quality_score": 0.9,
  "word_count": 150,
  "content_categories": ["tech"],
  "keywords": ["keyword1", "keyword2"]
}
```

### Adding Files for Processing

**Fresh Files (High Priority):**
```bash
cp your_data.jsonl toIndex/fresh/
```

**Backlog Files (Standard Priority):**
```bash
cp your_data.jsonl toIndex/backlog/
```

## Monitoring

### Log Output
The indexer provides comprehensive logging:
```
2025-08-24 10:30:15 - INFO - OpenSearch Indexer initialized successfully
2025-08-24 10:30:16 - INFO - Processing fresh file: /path/to/file.jsonl
2025-08-24 10:30:17 - INFO - Processed fresh file: /path/to/file.jsonl (1500 items)
2025-08-24 10:31:00 - INFO - Statistics - Uptime: 0.7h | Files: 45 processed, 2 failed | Fresh: 30 | Backlog: 15 | Docs: 1200 | Chunks: 3400 | Bulk ops: 45 | Errors: 0 | Queue: 0+0
```

### Key Metrics
- **Uptime**: Hours of continuous operation
- **Files Processed**: Successfully processed files
- **Fresh/Backlog**: Files processed by priority
- **Docs/Chunks**: Individual items indexed
- **Bulk Operations**: Number of bulk API calls
- **Queue Status**: High-priority + standard-priority queue sizes

## OpenSearch Index Structure

### Daily Indices
- Documents: `search_documents-YYYY-MM-DD`
- Chunks: `search_chunks-YYYY-MM-DD`

### Aliases
- `search_documents` → current daily document index
- `search_chunks` → current daily chunk index

### Templates
- Automatic index template creation
- Optimized mappings for search performance
- Configurable shards and replicas

## Production Deployment

### System Service (systemd)
Create `/etc/systemd/system/opensearch-indexer.service`:
```ini
[Unit]
Description=OpenSearch Indexer
After=network.target

[Service]
Type=simple
User=indexer
WorkingDirectory=/path/to/indexer
ExecStart=/usr/bin/python3 indexer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable opensearch-indexer
sudo systemctl start opensearch-indexer
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python3", "indexer.py"]
```

### Performance Optimization

1. **Queue Sizing**: Adjust queue sizes based on available memory
2. **Bulk Size**: Tune `BULK_CHUNK_SIZE` for your cluster capacity
3. **Polling Interval**: Balance responsiveness vs CPU usage
4. **OpenSearch Settings**: Configure cluster for bulk operations

### Monitoring Setup

1. **Log Monitoring**: Use tools like ELK stack or Grafana Loki
2. **Metrics Collection**: Export statistics to Prometheus
3. **Alerting**: Set up alerts for errors and queue overflow

## Troubleshooting

### Common Issues

**Queue Full Warnings:**
- Increase queue sizes in config
- Check OpenSearch cluster performance
- Verify network connectivity

**Connection Errors:**
- Verify OpenSearch host and credentials
- Check SSL/TLS settings
- Validate AWS credentials (if using AWS)

**File Processing Failures:**
- Check JSONL file format
- Verify file permissions
- Review error logs for specific issues

### Debug Mode
Set `LOG_LEVEL = "DEBUG"` in config for detailed output.

### Health Checks
The indexer performs automatic health checks every 5 minutes and logs cluster status.

## Security Considerations

1. **Credentials**: Use environment variables or secure credential stores
2. **File Permissions**: Restrict access to data directories
3. **Network Security**: Use SSL/TLS for OpenSearch connections
4. **AWS IAM**: Use minimal required permissions for AWS OpenSearch

## License

Production Indexer System - Internal Use

## Support

For issues and questions, review the logs and configuration settings. The indexer is designed for autonomous operation with comprehensive error handling and recovery mechanisms.
