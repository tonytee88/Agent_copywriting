import asyncio
import json
from email_orchestrator.tools.campaign_tools import plan_campaign

async def test_strategic_planner():
    print("Testing Strategic Planner...")
    
    # 1. Run Plan Campaign (this will trigger the new optimization layer)
    result = await plan_campaign(
        brand_name="PopBrush",
        campaign_goal="Promote the new 'Glitter Brush' specifically for holiday parties.",
        duration="3 days",
        total_emails=2,
        promotional_ratio=1.0 # Force promotional to test transformation logic
    )
    
    print("\n\n=== FINAL RESULT ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_strategic_planner())
