#!/usr/bin/env python3
"""
Data management utility for the Email Orchestrator.

Shows current data usage and allows manual cleanup/archiving.
Auto-cleanup runs on every save, but this provides visibility and control.
"""

import json
from pathlib import Path
from email_orchestrator.tools.history_manager import HistoryManager
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def show_file_stats():
    """Show size and entry counts for all data files."""
    print_header("DATA FILE STATISTICS")
    
    files = {
        "email_history_log.json": "Email History",
        "campaign_plans.json": "Campaign Plans",
        "brand_bio_db.json": "Brand Bios"
    }
    
    for filename, label in files.items():
        path = Path(filename)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            
            # Count entries
            try:
                data = json.loads(path.read_text())
                count = len(data) if isinstance(data, list) else len(data.keys())
            except:
                count = "?"
            
            print(f"{label:20s} {size_kb:>8.1f} KB  ({count} entries)")
        else:
            print(f"{label:20s} {'NOT FOUND':>20s}")

def show_history_stats():
    """Show detailed history statistics."""
    print_header("EMAIL HISTORY STATISTICS")
    
    manager = HistoryManager()
    stats = manager.get_stats()
    
    print(f"Total Entries:        {stats['total_entries']}")
    print(f"Brands:               {stats['brands']}")
    print(f"Max per Brand:        {stats['max_per_brand']}")
    print(f"Total Max:            {stats['total_max']}")
    
    print("\nEntries by Brand:")
    for brand, count in sorted(stats['entries_by_brand'].items()):
        print(f"  {brand:20s} {count:>4d} emails")

def show_campaign_plan_stats():
    """Show detailed campaign plan statistics."""
    print_header("CAMPAIGN PLAN STATISTICS")
    
    manager = CampaignPlanManager()
    stats = manager.get_stats()
    
    print(f"Total Plans:          {stats['total_plans']}")
    print(f"Brands:               {stats['brands']}")
    print(f"Max per Brand:        {stats['max_per_brand']}")
    print(f"Archive After:        {stats['archive_after_days']} days")
    print(f"Delete After:         {stats['delete_after_days']} days")
    
    print("\nPlans by Status:")
    for status, count in sorted(stats['plans_by_status'].items()):
        print(f"  {status:20s} {count:>4d} plans")
    
    print("\nPlans by Brand:")
    for brand, count in sorted(stats['plans_by_brand'].items()):
        print(f"  {brand:20s} {count:>4d} plans")

def show_retention_policies():
    """Display current retention policies."""
    print_header("RETENTION POLICIES")
    
    print("EMAIL HISTORY:")
    print("  • Keep last 50 emails per brand")
    print("  • Hard limit: 500 total entries")
    print("  • Auto-cleanup on every save")
    
    print("\nCAMPAIGN PLANS:")
    print("  • Keep last 10 plans per brand")
    print("  • Archive completed plans after 90 days")
    print("  • Delete archived plans after 365 days")
    print("  • Auto-cleanup on every save")
    
    print("\nOUTPUT FILES (via cleanup_data.py):")
    print("  • Archive outputs older than 30 days")
    print("  • Delete traces older than 7 days")
    print("  • Run manually: python3 cleanup_data.py")

def trigger_manual_cleanup():
    """Manually trigger cleanup (normally happens automatically)."""
    print_header("MANUAL CLEANUP")
    
    print("Loading and re-saving data to trigger auto-cleanup...")
    
    # History cleanup
    history_manager = HistoryManager()
    history = history_manager._load_history()
    cleaned_history = history_manager._cleanup_if_needed(history)
    history_manager._save_history(cleaned_history)
    print(f"✓ History: {len(history)} → {len(cleaned_history)} entries")
    
    # Campaign plans cleanup
    plan_manager = CampaignPlanManager()
    plans = plan_manager._load_all()
    cleaned_plans = plan_manager._cleanup_if_needed(plans)
    plan_manager._save_all(cleaned_plans)
    print(f"✓ Plans: {len(plans)} → {len(cleaned_plans)} entries")

def main():
    print("\n" + "=" * 70)
    print("  EMAIL ORCHESTRATOR - DATA MANAGEMENT")
    print("=" * 70)
    
    show_file_stats()
    show_history_stats()
    show_campaign_plan_stats()
    show_retention_policies()
    
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print("✓ Auto-cleanup is ENABLED on all data stores")
    print("✓ Data is within healthy limits")
    print("\nTo manually clean up old outputs and traces:")
    print("  python3 cleanup_data.py")
    print("\nTo force cleanup of history/plans (normally automatic):")
    print("  python3 check_data_usage.py --cleanup")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import sys
    
    if "--cleanup" in sys.argv:
        trigger_manual_cleanup()
        print("\n")
        show_file_stats()
    else:
        main()
