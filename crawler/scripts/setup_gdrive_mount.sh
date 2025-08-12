#!/bin/bash

# Google Drive Mount Setup Script
# This script sets up the rclone mount for direct Google Drive access

set -e

MOUNT_POINT="/mnt/gdrive-crawler"
RCLONE_REMOTE="rclone-gdrive"
REMOTE_PATH="RawHTML"

echo "🚀 Setting up Google Drive mount for crawler..."

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
    echo "❌ rclone is not installed. Please install rclone first."
    echo "   Visit: https://rclone.org/downloads/"
    exit 1
fi

# Check if rclone remote is configured
if ! rclone config show "$RCLONE_REMOTE" &> /dev/null; then
    echo "❌ rclone remote '$RCLONE_REMOTE' not found."
    echo "   Please configure rclone first: rclone config"
    exit 1
fi

# Create mount point directory
echo "📁 Creating mount point: $MOUNT_POINT"
sudo mkdir -p "$MOUNT_POINT"
sudo chown $USER:$USER "$MOUNT_POINT"

# Test rclone connection
echo "🔗 Testing rclone connection..."
if ! rclone lsd "$RCLONE_REMOTE:" &> /dev/null; then
    echo "❌ Failed to connect to Google Drive. Check your rclone configuration."
    exit 1
fi

# Create remote directory structure if it doesn't exist
echo "📂 Setting up remote directory structure..."
rclone mkdir "$RCLONE_REMOTE:$REMOTE_PATH" 2>/dev/null || true
rclone mkdir "$RCLONE_REMOTE:$REMOTE_PATH/daily" 2>/dev/null || true
rclone mkdir "$RCLONE_REMOTE:$REMOTE_PATH/live" 2>/dev/null || true

echo "✅ Google Drive mount setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. The crawler will automatically mount when started"
echo "   2. Files will be written directly to: $RCLONE_REMOTE:$REMOTE_PATH"
echo "   3. Local mount point: $MOUNT_POINT"
echo ""
echo "🔍 To manually test the mount:"
echo "   rclone mount $RCLONE_REMOTE:$REMOTE_PATH $MOUNT_POINT --daemon"
echo "   ls -la $MOUNT_POINT"
echo "   fusermount -u $MOUNT_POINT  # to unmount"
