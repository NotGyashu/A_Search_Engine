#!/bin/bash

# Script to sync existing HTML batch files to Google Drive
# This organizes files by date and uploads them to the correct Google Drive folders

echo "🔄 Starting sync of existing batch files to Google Drive..."

RAW_DATA_DIR="/home/gyashu/projects/A_Search_Engine/RawHTMLdata"
REMOTE_NAME="rclone-gdrive"
REMOTE_BASE="RawHTML"

# Check if rclone is configured
if ! rclone lsd ${REMOTE_NAME}: > /dev/null 2>&1; then
    echo "❌ Error: rclone remote '${REMOTE_NAME}' not configured or not accessible"
    exit 1
fi

echo "✅ rclone remote verified"

# Create a temporary directory for organizing files by date
TEMP_DIR="/tmp/rawhtml_sync"
mkdir -p "$TEMP_DIR"

echo "📁 Organizing files by date..."

# Process each batch file
for file in ${RAW_DATA_DIR}/batch_*.json; do
    if [[ -f "$file" ]]; then
        # Extract filename
        filename=$(basename "$file")
        
        # Extract date from filename (format: batch_YYYYMMDD_HHMMSS_NNN.json)
        if [[ $filename =~ batch_([0-9]{8})_[0-9]{6}_[0-9]+\.json ]]; then
            date_str="${BASH_REMATCH[1]}"
            # Convert YYYYMMDD to YYYY-MM-DD format
            formatted_date="${date_str:0:4}-${date_str:4:2}-${date_str:6:2}"
            
            # Create date directory in temp
            date_dir="${TEMP_DIR}/${formatted_date}"
            mkdir -p "$date_dir"
            
            # Copy file to date directory (don't move original)
            cp "$file" "$date_dir/"
            echo "📄 Organized: $filename -> $formatted_date/"
        else
            echo "⚠️  Warning: Could not parse date from filename: $filename"
        fi
    fi
done

echo ""
echo "📤 Uploading organized files to Google Drive..."

# Upload each date directory
for date_dir in ${TEMP_DIR}/*/; do
    if [[ -d "$date_dir" ]]; then
        date_name=$(basename "$date_dir")
        
        echo "🔄 Syncing $date_name..."
        
        # Create remote directory if it doesn't exist
        rclone mkdir "${REMOTE_NAME}:${REMOTE_BASE}/${date_name}"
        
        # Sync the directory
        file_count=$(ls -1 "$date_dir"/*.json 2>/dev/null | wc -l)
        if [[ $file_count -gt 0 ]]; then
            rclone copy "$date_dir" "${REMOTE_NAME}:${REMOTE_BASE}/${date_name}/" -v --stats 1s
            echo "✅ Synced $file_count files for $date_name"
        else
            echo "⚠️  No files found for $date_name"
        fi
    fi
done

echo ""
echo "🧹 Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo ""
echo "📊 Verifying sync results..."
echo "Google Drive folder structure:"
rclone tree "${REMOTE_NAME}:${REMOTE_BASE}" --dirs-only

echo ""
echo "✅ Sync complete! Checking file counts per date:"
for date_dir in $(rclone lsd "${REMOTE_NAME}:${REMOTE_BASE}" | grep -E '[0-9]{4}-[0-9]{2}-[0-9]{2}' | awk '{print $NF}'); do
    file_count=$(rclone ls "${REMOTE_NAME}:${REMOTE_BASE}/${date_dir}" | wc -l)
    echo "📁 ${date_dir}: ${file_count} files"
done

echo ""
echo "🎉 All existing files have been synced to Google Drive!"
echo "💡 Future files will be automatically synced when the crawler runs."
