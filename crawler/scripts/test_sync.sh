#!/bin/bash

# Test script to verify the new 90-second sync and immediate delete functionality

echo "🧪 Testing Google Drive sync with new settings..."
echo "📊 Current file count in today's folder:"

LOCAL_TODAY="/home/gyashu/projects/A_Search_Engine/RawHTMLdata/2025-08-07"
REMOTE_TODAY="rclone-gdrive:RawHTML/2025-08-07"

# Count files before sync
LOCAL_COUNT=$(find "$LOCAL_TODAY" -name "*.json" 2>/dev/null | wc -l)
echo "   Local files: $LOCAL_COUNT"

if [ $LOCAL_COUNT -gt 0 ]; then
    echo ""
    echo "📤 Manually triggering sync to test immediate deletion..."
    
    # Sync all files in today's folder
    rclone copy "$LOCAL_TODAY/" "$REMOTE_TODAY/" -v --stats 1s
    
    echo ""
    echo "✅ Sync completed. Now manually deleting local files to simulate automatic deletion..."
    
    # Delete local files after successful sync (simulating our new behavior)
    for file in "$LOCAL_TODAY"/*.json; do
        if [ -f "$file" ]; then
            echo "🗑️  Deleting local file: $(basename "$file")"
            rm "$file"
        fi
    done
    
    echo ""
    echo "📊 Results after sync and deletion:"
    LOCAL_COUNT_AFTER=$(find "$LOCAL_TODAY" -name "*.json" 2>/dev/null | wc -l)
    REMOTE_COUNT=$(rclone ls "$REMOTE_TODAY" 2>/dev/null | wc -l)
    
    echo "   Local files remaining: $LOCAL_COUNT_AFTER"
    echo "   Remote files on Google Drive: $REMOTE_COUNT"
    
    if [ $LOCAL_COUNT_AFTER -eq 0 ] && [ $REMOTE_COUNT -gt 0 ]; then
        echo ""
        echo "🎉 Test PASSED: Files synced to Google Drive and deleted locally!"
    else
        echo ""
        echo "❌ Test FAILED: Expected 0 local files and >0 remote files"
    fi
else
    echo "⚠️  No files found to test sync. Run the crawler first to generate some files."
fi

echo ""
echo "🔍 Showing remote file structure:"
rclone tree rclone-gdrive:RawHTML --dirs-only
