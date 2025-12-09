#!/usr/bin/env python3
"""
Cleanup script for email orchestrator data management.

This script:
1. Archives email outputs older than 30 days
2. Deletes trace files older than 7 days
3. Compresses old archives

Run manually or via cron job.
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
OUTPUTS_DIR = Path("outputs")
TRACES_DIR = Path("traces")
ARCHIVE_DAYS = 30
TRACE_RETENTION_DAYS = 7


def archive_old_outputs():
    """Move outputs older than ARCHIVE_DAYS to archive/YYYY-MM/"""
    if not OUTPUTS_DIR.exists():
        print("No outputs directory found")
        return
    
    cutoff_date = datetime.now() - timedelta(days=ARCHIVE_DAYS)
    archived_count = 0
    
    for file in OUTPUTS_DIR.glob("*.txt"):
        # Get file modification time
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        
        if mtime < cutoff_date:
            # Create archive directory for this month
            archive_month = mtime.strftime("%Y-%m")
            archive_dir = OUTPUTS_DIR / "archive" / archive_month
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file
            dest = archive_dir / file.name
            shutil.move(str(file), str(dest))
            archived_count += 1
            print(f"Archived: {file.name} -> {archive_month}/")
    
    print(f"✓ Archived {archived_count} old output files")


def cleanup_old_traces():
    """Delete trace files older than TRACE_RETENTION_DAYS"""
    if not TRACES_DIR.exists():
        print("No traces directory found")
        return
    
    cutoff_date = datetime.now() - timedelta(days=TRACE_RETENTION_DAYS)
    deleted_count = 0
    
    for file in TRACES_DIR.glob("*.json"):
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        
        if mtime < cutoff_date:
            file.unlink()
            deleted_count += 1
            print(f"Deleted trace: {file.name}")
    
    print(f"✓ Deleted {deleted_count} old trace files")


def print_storage_stats():
    """Print current storage usage"""
    print("\n" + "="*50)
    print("Storage Statistics")
    print("="*50)
    
    for path in ["email_history_log.json", "brand_bio_db.json", "outputs/", "traces/"]:
        p = Path(path)
        if p.exists():
            if p.is_file():
                size = p.stat().st_size / 1024  # KB
                print(f"{path:30s} {size:>8.1f} KB")
            else:
                # Directory size
                total = sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
                size = total / 1024
                count = len(list(p.rglob('*.txt' if 'outputs' in str(p) else '*.json')))
                print(f"{path:30s} {size:>8.1f} KB ({count} files)")
    
    print("="*50 + "\n")


if __name__ == "__main__":
    print("Email Orchestrator Data Cleanup")
    print("="*50)
    
    print_storage_stats()
    
    print("Running cleanup...")
    archive_old_outputs()
    cleanup_old_traces()
    
    print("\n✓ Cleanup complete!")
    print_storage_stats()
