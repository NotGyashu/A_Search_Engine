# Google Drive Sync Integration for Web Crawler

This integration allows the web crawler to automatically sync raw HTML data to Google Drive using rclone, providing cloud storage and backup capabilities.

## Features

- **Automatic Google Drive sync** - Raw crawled HTML files are automatically uploaded to Google Drive
- **Mode-specific organization** - Files are organized differently based on crawler mode:
  - **Regular Mode**: Daily archive folders (`RawHTML/YYYY-MM-DD/`)
  - **Fresh Mode**: Live workspace folder (`RawHTML/Live/`) with real-time sync
- **Temporary local storage** - Local disk is used only temporarily until files are uploaded
- **Background sync operations** - Non-blocking sync operations that don't affect crawl performance
- **Error handling and logging** - Comprehensive error handling with detailed logging

## Prerequisites

### 1. Install rclone

```bash
# On Ubuntu/Debian
sudo apt install rclone

# Or download directly
curl https://rclone.org/install.sh | sudo bash
```

### 2. Configure Google Drive Remote

```bash
# Start rclone configuration
rclone config

# Follow these steps:
# 1. Choose "n" for new remote
# 2. Name: rclone-gdrive
# 3. Storage type: drive (Google Drive)
# 4. Follow the OAuth flow to authenticate
```

Your `.env` file should contain:
```properties
rclone_client_id=your-google-oauth-client-id
rclone_client_secret=your-google-oauth-client-secret
```

### 3. Verify Configuration

```bash
# Test the remote configuration
rclone lsd rclone-gdrive:

# Should show your Google Drive folders
```

## Directory Structure

The crawler creates the following structure both locally and on Google Drive:

```
RawHTML/
├── 2025-08-07/          # Daily archive (Regular mode)
│   ├── batch_20250807_100530_001.json
│   ├── batch_20250807_100535_002.json
│   └── ...
├── 2025-08-08/          # Next day's archive
│   └── ...
└── Live/                # Live workspace (Fresh mode)
    ├── batch_20250807_145230_001.json
    ├── batch_20250807_145235_002.json
    └── ...
```

## How It Works

### Regular Mode (Deep Crawling)
1. Crawler saves JSON files to local directory: `RawHTML/YYYY-MM-DD/`
2. Background sync thread runs every 90 seconds
3. Files are uploaded to Google Drive: `rclone-gdrive:RawHTML/YYYY-MM-DD/`
4. After successful upload, local files are immediately deleted to save disk space

### Fresh Mode (Real-time RSS/Atom)
1. Crawler saves JSON files to local directory: `RawHTML/Live/`
2. Background sync thread runs every 90 seconds
3. Files are uploaded to Google Drive: `rclone-gdrive:RawHTML/Live/`
4. After successful upload, local files are immediately deleted to save disk space

## Configuration

The Google Drive sync is automatically enabled when:
1. rclone is installed and configured
2. The remote "rclone-gdrive" exists and is accessible
3. The crawler can create the necessary directories

If Google Drive sync fails to initialize, the crawler automatically falls back to local-only storage.

## File Format

JSON files maintain the same format as before but are now organized by date and sync mode:

```json
[
  {
    "url": "https://example.com/page1",
    "domain": "example.com",
    "title": "Example Page",
    "text_snippet": "This is a snippet...",
    "timestamp": "2025-08-07T10:05:30Z",
    "depth": 1,
    "http_status_code": 200,
    "content_length": 45678,
    "content_hash": "abc123...",
    "last_crawl_time": "2025-08-07T10:05:30Z",
    "content": "<!DOCTYPE html>..."
  }
]
```

## Monitoring and Troubleshooting

### Check Sync Status
The crawler provides real-time feedback on sync operations:

```
✅ Google Drive sync enabled for REGULAR mode
🔄 Starting background Google Drive sync for REGULAR mode
✅ Synced to Google Drive [daily]: batch_20250807_100530_001.json
🗑️  Deleted local file after sync [daily]: batch_20250807_100530_001.json
```

### Common Issues

#### "rclone remote not configured"
```bash
# Reconfigure rclone
rclone config
```

#### "Failed to create remote directories"
```bash
# Check Google Drive permissions
rclone lsd rclone-gdrive:
```

#### "Background sync error"
Check that:
- Internet connection is stable
- Google Drive has sufficient space
- rclone configuration is valid

### Manual Sync
You can manually sync files if needed:

```bash
# Sync a specific day's archive
rclone copy /path/to/RawHTML/2025-08-07/ rclone-gdrive:RawHTML/2025-08-07/

# Sync live workspace
rclone copy /path/to/RawHTML/Live/ rclone-gdrive:RawHTML/Live/
```

## Performance Impact

- **Minimal crawling impact**: Sync operations run in background threads
- **Bandwidth usage**: Upload bandwidth proportional to crawl rate
- **Local storage**: Significantly reduced (files deleted after successful sync in Regular mode)
- **Memory usage**: Minimal additional memory footprint

## Security Considerations

- OAuth tokens are stored securely by rclone
- Files are encrypted in transit to Google Drive
- No sensitive data is logged in sync operations
- Local files are properly cleaned up after sync

## Bandwidth Estimation

Typical usage:
- **Regular mode**: ~100-500 MB/hour (depending on crawl rate)
- **Fresh mode**: ~50-200 MB/hour (RSS/Atom content)
- **Peak usage**: Up to 1-2 GB/hour during intensive crawling

Ensure your internet connection can handle the upload requirements for your expected crawl volume.
