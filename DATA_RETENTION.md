# Data Retention & Cleanup Strategy

## Overview

The Email Orchestrator has **automatic cleanup** built into all data stores to prevent unbounded growth. Data is cleaned up on every save operation, so no manual intervention is needed under normal operation.

---

## Current Status

**Data Usage** (as of now):
- Email History: 15.8 KB (4 entries)
- Campaign Plans: 19.1 KB (3 entries)  
- Brand Bios: 1.9 KB (2 entries)

✅ **All data is well within healthy limits**

---

## Retention Policies

### 1. Email History (`email_history_log.json`)

**Auto-cleanup triggers on every `log_campaign()` call**

**Limits:**
- **50 emails per brand** (keeps last 50)
- **500 total entries** across all brands (hard limit)

**Strategy:**
1. Group entries by brand
2. Keep last 50 emails per brand
3. If still over 500 total, keep newest 500 across all brands

**Why 50 per brand?**
- Campaign Planner uses last 20 for context
- Verifier checks last 10 for repetition
- 50 provides good buffer for variety checking

---

### 2. Campaign Plans (`campaign_plans.json`)

**Auto-cleanup triggers on every `save_plan()` call**

**Limits:**
- **10 plans per brand** (keeps last 10 active plans)
- **Archive completed plans after 90 days**
- **Delete archived plans after 365 days**

**Strategy:**
1. Delete archived plans older than 1 year
2. Archive completed plans older than 90 days
3. Keep last 10 active plans per brand

**Status Lifecycle:**
```
draft → approved → in_progress → completed → archived → deleted
                                    ↓ 90 days    ↓ 365 days
```

---

### 3. Output Files & Traces

**Manual cleanup via `cleanup_data.py`**

**Policies:**
- Archive email outputs older than **30 days** → `outputs/archive/YYYY-MM/`
- Delete trace files older than **7 days**

**Run manually:**
```bash
python3 cleanup_data.py
```

---

## Monitoring

### Check Current Usage

```bash
python3 check_data_usage.py
```

**Shows:**
- File sizes and entry counts
- Entries per brand
- Plans by status
- Current retention policies

### Force Manual Cleanup

```bash
python3 check_data_usage.py --cleanup
```

This re-triggers auto-cleanup (normally happens automatically on save).

---

## Thresholds & Triggers

| Data Store | Trigger | Threshold | Action |
|------------|---------|-----------|--------|
| Email History | Every save | 50/brand | Keep last 50 per brand |
| Email History | Every save | 500 total | Keep newest 500 overall |
| Campaign Plans | Every save | 10/brand | Keep last 10 active per brand |
| Campaign Plans | Every save | 90 days | Archive completed plans |
| Campaign Plans | Every save | 365 days | Delete archived plans |
| Output Files | Manual | 30 days | Archive to `outputs/archive/` |
| Trace Files | Manual | 7 days | Delete |

---

## Why These Limits?

### Email History (50 per brand)
- ✅ Campaign Planner needs 20 for context
- ✅ Verifier needs 10 for repetition checks
- ✅ 50 provides good variety checking buffer
- ✅ Prevents unbounded growth
- ✅ At ~4KB per entry, 500 entries = ~2MB (very manageable)

### Campaign Plans (10 per brand)
- ✅ Most brands won't have >10 active campaigns
- ✅ Old completed plans auto-archive
- ✅ Archived plans eventually delete
- ✅ At ~6KB per plan, 10 plans = ~60KB per brand

### Output Files (30 days)
- ✅ Recent outputs easily accessible
- ✅ Old outputs archived by month
- ✅ Can retrieve from archive if needed

### Trace Files (7 days)
- ✅ Debugging traces kept for recent runs
- ✅ Old traces not needed (can regenerate)

---

## Adjusting Limits

To change retention limits, edit the constants in:

**Email History:**
```python
# email_orchestrator/tools/history_manager.py
MAX_ENTRIES_PER_BRAND = 50
TOTAL_MAX_ENTRIES = 500
```

**Campaign Plans:**
```python
# email_orchestrator/tools/campaign_plan_manager.py
MAX_PLANS_PER_BRAND = 10
ARCHIVE_COMPLETED_AFTER_DAYS = 90
DELETE_ARCHIVED_AFTER_DAYS = 365
```

**Output Files:**
```python
# cleanup_data.py
ARCHIVE_DAYS = 30
TRACE_RETENTION_DAYS = 7
```

---

## Best Practices

1. **Monitor periodically**: Run `python3 check_data_usage.py` monthly
2. **Clean outputs**: Run `python3 cleanup_data.py` monthly
3. **Archive important campaigns**: Export campaign plans before they're deleted
4. **Adjust limits**: If you have many brands, consider increasing limits

---

## Summary

✅ **Auto-cleanup is ENABLED** on all data stores  
✅ **No manual intervention needed** under normal operation  
✅ **Current data usage is healthy** (well under limits)  
✅ **Monitoring tools available** for visibility  

The system is designed to be **self-maintaining** while keeping enough history for quality checks and variety enforcement.
