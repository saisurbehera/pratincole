#!/usr/bin/env python3
import os
import shutil
import time
import datetime

# Source and destination directories
SRC_DIR = "/home/sai/Desktop/factorio/pratincole/wiki/forum_pages"
DEST_DIR = "/mnt/sai/factorio_forum"

def sync_files():
    """Move files from source to destination directory, but only those matching _viewtopic pattern"""
    # Create destination directory if it doesn't exist
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        print(f"Created destination directory: {DEST_DIR}")
    
    # Get list of files in source directory
    try:
        all_files = os.listdir(SRC_DIR)
        
        # Filter for only _viewtopic files
        viewtopic_files = [f for f in all_files if "_viewtopic" in f]
        
        if not viewtopic_files:
            print(f"{datetime.datetime.now()}: No _viewtopic files to sync")
            return
            
        print(f"{datetime.datetime.now()}: Moving {len(viewtopic_files)} _viewtopic files to {DEST_DIR}")
        
        # Move each file
        moved_count = 0
        for filename in viewtopic_files:
            src_path = os.path.join(SRC_DIR, filename)
            dest_path = os.path.join(DEST_DIR, filename)
            
            # Only move files, not directories
            if os.path.isfile(src_path):
                shutil.move(src_path, dest_path)
                moved_count += 1
                
        print(f"Moved {moved_count} _viewtopic files")
    
    except Exception as e:
        print(f"Error during sync: {e}")

def main():
    print(f"Starting file sync from {SRC_DIR} to {DEST_DIR}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            sync_files()
            time.sleep(60)  # Sleep for 60 seconds (1 minute)
    
    except KeyboardInterrupt:
        print("\nSync stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()