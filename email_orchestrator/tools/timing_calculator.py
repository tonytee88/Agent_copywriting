from datetime import datetime, timedelta
from typing import List, Dict, Optional

def calculate_send_schedule(
    start_date: datetime,
    total_emails: int,
    duration_str: str = "1 month",
    excluded_days: List[str] = []
) -> List[Dict[str, str]]:
    """
    Calculate email send schedule.
    Rule:
    - Email 1: STRICTLY on start_date.
    - Subsequent Emails: Snap to next Thursday/Sunday grid.
    - Cadence: 2-3 emails/week based on volume.
    - Exclusions: Skip matches in excluded_days.
    """
    # 1. Normalize exclusions
    exclusions_normalized = [d.lower() for d in excluded_days]

    # 2. Determine Deadline
    # For now, simplistic deadline calculation based on duration
    # If duration is a month name, end of that month in the start_date's year
    deadline = None
    if any(m in duration_str.lower() for m in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]):
        # It's likely a specific month request.
        # Find the last day of the start_date's month
        import calendar
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        deadline = start_date.replace(day=last_day)
    elif "week" in duration_str.lower():
         try:
             weeks = int(duration_str.split()[0])
             deadline = start_date + timedelta(weeks=weeks)
         except:
             deadline = start_date + timedelta(days=30)
    else:
        # Default 30 days
        deadline = start_date + timedelta(days=30)

    print(f"[Timing] Calculated Deadline: {deadline.strftime('%Y-%m-%d')}")

    # 3. Define Strategies
    strategies = [
        {"name": "Standard (Thu/Sun)", "high_freq": False, "interval": None},
        {"name": "High Freq (Tue/Thu/Sun)", "high_freq": True, "interval": None},
        {"name": "Compressed (Every 3 Days)", "high_freq": False, "interval": 3},
        {"name": "Rapid (Every 2 Days)", "high_freq": False, "interval": 2},
        {"name": "Daily (Maximize)", "high_freq": False, "interval": 1}
    ]

    # 1. Define First Email (Fixed)
    first_email = {
        "email_num": 1,
        "day": start_date.strftime("%A"),
        "date": start_date.strftime("%Y-%m-%d"),
        "time": "7:00 AM"
    }

    final_schedule = []
    
    for strategy in strategies:
        temp_schedule = []
        temp_email_count = 1 # Already have correct first email
        temp_current_date = start_date # Start from first email
        
        # Add the first fixed email
        temp_schedule.append(first_email)
        
        failed_strategy = False
        
        while temp_email_count < total_emails:
            # Advance logic
            if strategy["interval"]:
                temp_current_date += timedelta(days=strategy["interval"])
            else:
                temp_current_date += timedelta(days=1)
            
            day_name = temp_current_date.strftime("%A")
            weekday = temp_current_date.weekday() # Mon=0, Sun=6
            
            # 1. Global Exclusion Check
            if day_name.lower() in exclusions_normalized:
                continue
            
            # 2. Grid Check (Only if not using naive interval)
            is_send_day = False
            time = "7:00 AM"
            
            if strategy["interval"]:
                # If using interval, any non-excluded day is valid
                is_send_day = True
            else:
                # Use Grid
                if weekday == 3: # Thursday
                    is_send_day = True
                elif weekday == 6: # Sunday
                    is_send_day = True
                    time = "7:00 PM"
                elif strategy["high_freq"] and weekday == 1: # Tuesday
                    is_send_day = True
            
            if is_send_day:
                temp_schedule.append({
                    "email_num": temp_email_count + 1,
                    "day": day_name,
                    "date": temp_current_date.strftime("%Y-%m-%d"),
                    "time": time
                })
                temp_email_count += 1
                
            # Safety break for infinite loops
            if (temp_current_date - start_date).days > 60:
                break
        
        # Check if strategy worked (Last email <= Deadline)
        if temp_schedule and len(temp_schedule) == total_emails:
            last_date_str = temp_schedule[-1]["date"]
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            
            if last_date <= deadline:
                print(f"[Timing] Strategy '{strategy['name']}' SUCCESS. Ends: {last_date_str}")
                final_schedule = temp_schedule
                break
            else:
                print(f"[Timing] Strategy '{strategy['name']}' failed. Ends {last_date_str} > {deadline.strftime('%Y-%m-%d')}")
        else:
             print(f"[Timing] Strategy '{strategy['name']}' failed to generate enough emails.")

    # Fallback: if all strategies fail, return the last generated one (likely Daily or compressed)
    # or just return the Standard one even if it overruns (better than nothing)
    if not final_schedule and strategies: 
        print("[Timing] All strategies failed strict deadline. Returning best effort (last calculation).")
        # Re-run last strategy just to fit the list
        final_schedule = temp_schedule 

    return final_schedule

def get_next_thursday(from_date: Optional[datetime] = None) -> datetime:
    """Get the next Thursday from the given date (or today)."""
    if from_date is None:
        from_date = datetime.now()
    
    days_until_thursday = (3 - from_date.weekday()) % 7
    if days_until_thursday == 0:
        # If today is Thursday, check if it's past 7PM
        if from_date.hour >= 19:
            days_until_thursday = 7
    
    next_thursday = from_date + timedelta(days=days_until_thursday)
    return next_thursday.replace(hour=7, minute=0, second=0, microsecond=0)

def parse_duration_to_start_date(duration_str: str) -> datetime:
    """
    Parse duration string to determine start date.
    
    Examples:
    - "next month" → First Thursday of next calendar month
    - "1 month" → Next Thursday
    - "30 days" → Next Thursday
    - "next week" → Next Thursday
    """
    now = datetime.now()
    duration_lower = duration_str.lower()
    
    if "next month" in duration_lower:
        # First Thursday of next calendar month
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        return get_next_thursday(next_month)
    else:
        # Default: next Thursday from now
        return get_next_thursday(now)

def parse_readable_date(date_str: str) -> Optional[datetime]:
    """
    Attempts to parse a human-readable date string into a datetime object.
    Supports: "YYYY-MM-DD", "Jan 7", "January 7th", "7 Jan 2026".
    """
    import re
    from datetime import datetime
    
    clean_str = date_str.strip()
    
    # Try ISO format first
    try:
        return datetime.strptime(clean_str, "%Y-%m-%d")
    except ValueError:
        pass
        
    # Remove ordinal suffixes (st, nd, rd, th)
    clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_str)
    
    # Try common formats
    formats = [
        "%b %d",        # Jan 7
        "%B %d",        # January 7
        "%d %b",        # 7 Jan
        "%d %B",        # 7 January
        "%b %d %Y",     # Jan 7 2026
        "%B %d %Y",     # January 7 2026
        "%Y %b %d",     # 2026 Jan 7
    ]
    
    current_year = datetime.now().year
    
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_str, fmt)
            # If no year parsed, assume next occurrence of this date
            if dt.year == 1900:
                dt = dt.replace(year=current_year)
                # If date is in past, move to next year (unless it's Jan and we are in Dec, etc. logic implies forward looking)
                # Simple logic: if date is more than 30 days in past, assume next year.
                if dt < datetime.now() - timedelta(days=30):
                    dt = dt.replace(year=current_year + 1)
            return dt
        except ValueError:
            continue
            
    return None
