# Quick Start Guide - Campaign Planner

## Using the Campaign Planner via main.py

The Campaign Planner is **fully integrated** into the main orchestrator. You can use it through the CLI:

```bash
python3 main.py
```

---

## Available Commands

### 1. Analyze a Brand (First Time Setup)

```
> Analyze the brand at https://popbrush.fr/
```

**What happens:**
- Scrapes website
- Creates Brand Bio
- Saves to database

---

### 2. Plan a Campaign

```
> Plan a 7-email campaign for PopBrush with the goal: Build awareness about hair health, then drive Black Friday sales
```

**What happens:**
- Campaign Planner creates strategic plan
- Verifier checks quality
- Auto-revises if needed
- Saves approved plan
- Returns campaign ID

**You can also specify:**
```
> Plan a 10-email campaign for PopBrush over next month with 40% promotional ratio. Goal: Launch new product line
```

---

### 3. Generate Email from Campaign Plan

**Option A: Specify slot number**
```
> Generate email #1 from campaign plan 20240822143215 for PopBrush
```

**Option B: Use next available slot**
```
> Generate next email from campaign 20240822143215 for PopBrush
```

**What happens:**
- Loads campaign plan
- Gets slot directives (transformation, angle, structure, persona)
- Strategist creates blueprint using directives
- Drafter writes email
- Verifier checks quality (with revision loop)
- Saves to outputs/

---

### 4. Generate Standalone Email (Old Way)

```
> Generate an email for PopBrush with offer "25% off" and angle "Black Friday urgency"
```

**Still works!** But campaign-driven is better for multi-email sequences.

---

## Example Workflow

### Full Campaign Workflow

```bash
# Terminal 1: Start the orchestrator
python3 main.py

# Step 1: Analyze brand (if not done)
> Analyze the brand at https://popbrush.fr/

# Step 2: Plan campaign
> Plan a 7-email campaign for PopBrush. Goal: Build awareness then drive Black Friday sales

# (Copy the campaign ID from response, e.g., "20240822143215")

# Step 3: Generate emails one by one
> Generate email #1 from campaign 20240822143215 for PopBrush
> Generate email #2 from campaign 20240822143215 for PopBrush
> Generate email #3 from campaign 20240822143215 for PopBrush
# ... etc
```

---

## How the Orchestrator Understands

The orchestrator (Gemini) has access to these tools:

1. **`analyze_brand(website_url)`** - Scrapes and saves brand info
2. **`plan_campaign(brand_name, campaign_goal, total_emails, duration, promotional_ratio)`** - Creates campaign plan
3. **`generate_email_campaign(brand_name, offer, angle, transformation, campaign_plan_id, slot_number)`** - Generates email

**Natural language examples it understands:**

✅ "Plan a campaign for PopBrush"
✅ "Create a 10-email sequence for PopBrush about Black Friday"
✅ "Generate the first email from campaign 123"
✅ "Write email #3 from the PopBrush campaign"
✅ "Generate next email from campaign plan 20240822143215"

---

## Checking Campaign Status

### Via Python Script

```bash
python3 check_data_usage.py
```

Shows:
- All campaign plans
- Plans by brand
- Plans by status

### Via JSON File

```bash
cat campaign_plans.json | jq '.[] | {id: .campaign_id, name: .campaign_name, status: .status}'
```

---

## Tips

### 1. Campaign Planning Best Practices

- **Start with 5-7 emails** for testing
- **Use clear goals** (e.g., "Build awareness then drive sales")
- **Default ratio is good** (40% promo, 60% educational)
- **Let it auto-adjust timing** (2-3 emails/week)

### 2. Email Generation Best Practices

- **Generate in sequence** (1, 2, 3...) for best flow
- **Review outputs** in `outputs/` directory
- **Check connections** between emails
- **Track progress** (mark campaign as "in_progress")

### 3. Troubleshooting

**"Brand not found"**
→ Run `analyze_brand` first

**"Campaign plan not found"**
→ Check campaign ID is correct
→ Run `cat campaign_plans.json` to see all plans

**"Verification failed"**
→ Auto-revision should handle it
→ If still fails after 2 retries, check feedback

---

## Advanced Usage

### Update Campaign Status

```python
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

manager = CampaignPlanManager()
manager.update_plan_status("20240822143215", "in_progress")
manager.update_plan_status("20240822143215", "completed")
```

### Get Campaign Info

```python
plan = manager.get_plan("20240822143215")
print(f"Campaign: {plan.campaign_name}")
print(f"Emails: {plan.total_emails}")
print(f"Status: {plan.status}")

for slot in plan.email_slots:
    print(f"Email #{slot.slot_number}: {slot.theme}")
```

---

## Summary

✅ **Fully integrated** into main.py
✅ **Natural language** commands work
✅ **Three main tools** available:
   - analyze_brand
   - plan_campaign
   - generate_email_campaign
✅ **Campaign-driven** email generation ready
✅ **Auto-cleanup** keeps data manageable

Just run `python3 main.py` and start planning campaigns! 🚀
