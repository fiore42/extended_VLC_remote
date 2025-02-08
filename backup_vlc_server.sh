#!/bin/bash


# Get current date in YYYYMMDD_HHMMSS format
DATE=$(date +%Y%m%d_%H%M%S)

# Define archive name
ARCHIVE_NAME="vlc_server_${DATE}.tgz"

# Define the folder to backup (assumes script is inside the same folder)
FOLDER_TO_BACKUP="$(pwd)"

# Create the tar.gz archive while excluding .tgz files
tar --exclude="*.tgz" -czf "$ARCHIVE_NAME" -C "$FOLDER_TO_BACKUP" .

# Print confirmation
echo "Backup created: $ARCHIVE_NAME"
