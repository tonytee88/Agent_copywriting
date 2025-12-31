from datetime import datetime, timedelta
from typing import List, Dict, Optional

def calculate_send_schedule(
    start_date: datetime,
    total_emails: int,
    duration_str: str = "1 month"
) -> List[Dict[str, str]]:
    """
    Calculate email send schedule.
    Rule:
    - Email 1: STRICTLY on start_date.
    - Subsequent Emails: Snap to next Thursday/Sunday grid.
    - Cadence: 2-3 emails/week based on volume.
    """
    schedule = []
    current_date = start_date
    email_count = 0
    
    # 1. Schedule First Email
    schedule.append({
        "email_num": 1,
        "day": current_date.strftime("%A"),
        "date": current_date.strftime("%Y-%m-%d"),
        "time": "7:00 AM" # Default start time
    })
    email_count += 1
    
    if email_count >= total_emails:
        return schedule
        
    # Determine density
    estimated_weeks = 4
    if "week" in duration_str.lower():
        try:
            estimated_weeks = int(duration_str.split()[0])
        except:
            pass
    emails_per_week = total_emails / max(1, estimated_weeks)
    use_high_freq = emails_per_week > 2.5
    
    # Advance to next grid slot (Thursday or Sunday)
    # Grid days: Thursday (3), Sunday (6)
    # If high freq, also Tuesday (1)
    
    while email_count < total_emails:
        current_date += timedelta(days=1)
        weekday = current_date.weekday()
        
        is_send_day = False
        time = "7:00 AM"
        
        if weekday == 3: # Thursday
            is_send_day = True
            time = "7:00 AM" # Simplified
        elif weekday == 6: # Sunday
            is_send_day = True
            time = "7:00 PM"
        elif use_high_freq and weekday == 1: # Tuesday
            is_send_day = True
            time = "7:00 AM"
            
        if is_send_day:
            schedule.append({
                "email_num": email_count + 1,
                "day": current_date.strftime("%A"),
                "date": current_date.strftime("%Y-%m-%d"),
                "time": time
            })
            email_count += 1
            
    return schedule

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
