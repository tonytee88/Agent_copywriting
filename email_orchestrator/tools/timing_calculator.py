from datetime import datetime, timedelta
from typing import List, Dict, Optional

def calculate_send_schedule(
    start_date: datetime,
    total_emails: int,
    duration_str: str = "1 month"
) -> List[Dict[str, str]]:
    """
    Calculate email send schedule based on best practice timing rules.
    
    Rules:
    - Default: 2 emails per week (Thursday + Sunday)
    - If >2/week needed: Auto-adjust to 3/week (Thursday, Sunday, + 1 midweek)
    - Thursday: Alternate between 7:00 PM and 7:00 AM (every 3rd send)
    - Sunday: Always 7:00 PM (only 1 per week)
    - Midweek (for 3/week): Tuesday or Wednesday, 7:00 AM
    
    Args:
        start_date: Campaign start date
        total_emails: Number of emails to schedule
        duration_str: Duration string (e.g., "1 month", "4 weeks")
    
    Returns:
        List of schedule entries with email_num, day, date, time
    """
    schedule = []
    current_date = start_date
    email_count = 0
    thursday_count = 0
    week_count = 0
    
    # Determine emails per week
    estimated_weeks = 4  # Default assumption
    if "week" in duration_str.lower():
        try:
            estimated_weeks = int(duration_str.split()[0])
        except:
            pass
    
    emails_per_week = total_emails / estimated_weeks
    use_three_per_week = emails_per_week > 2
    
    # Find next Thursday from start date
    days_until_thursday = (3 - current_date.weekday()) % 7
    if days_until_thursday == 0 and current_date.hour >= 19:
        days_until_thursday = 7
    current_date = current_date + timedelta(days=days_until_thursday)
    
    while email_count < total_emails:
        day_of_week = current_date.weekday()
        
        # Thursday (3)
        if day_of_week == 3:
            thursday_count += 1
            # Every 3rd Thursday send at 7PM, otherwise 7AM
            time = "7:00 PM" if thursday_count % 3 == 0 else "7:00 AM"
            
            schedule.append({
                "email_num": email_count + 1,
                "day": "Thursday",
                "date": current_date.strftime("%Y-%m-%d"),
                "time": time
            })
            email_count += 1
            
            if email_count >= total_emails:
                break
            
            # Add midweek email if using 3/week (Tuesday or Wednesday)
            if use_three_per_week:
                # Alternate between Tuesday (5 days back) and Wednesday (4 days back)
                days_to_midweek = -5 if week_count % 2 == 0 else -4
                midweek_date = current_date + timedelta(days=days_to_midweek)
                midweek_day = "Tuesday" if week_count % 2 == 0 else "Wednesday"
                
                # Only add if we haven't exceeded total
                if email_count < total_emails:
                    schedule.insert(len(schedule) - 1, {  # Insert before Thursday
                        "email_num": email_count + 1,
                        "day": midweek_day,
                        "date": midweek_date.strftime("%Y-%m-%d"),
                        "time": "7:00 AM"
                    })
                    email_count += 1
                    
                    # Re-number emails after insertion
                    for i, slot in enumerate(schedule):
                        slot["email_num"] = i + 1
            
            if email_count >= total_emails:
                break
            
            # Move to Sunday (3 days later)
            current_date += timedelta(days=3)
            
        # Sunday (6)
        elif day_of_week == 6:
            schedule.append({
                "email_num": email_count + 1,
                "day": "Sunday",
                "date": current_date.strftime("%Y-%m-%d"),
                "time": "7:00 PM"
            })
            email_count += 1
            
            if email_count >= total_emails:
                break
            
            # Move to next Thursday (4 days later)
            current_date += timedelta(days=4)
            week_count += 1
    
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
