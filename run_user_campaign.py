import asyncio
import json
from email_orchestrator.tools.campaign_tools import plan_campaign, generate_email_campaign

async def main():
    print("=== STARTING USER CAMPAIGN ===")
    
    # 1. Plan
    plan_output = await plan_campaign(
        brand_name="PopBrush",
        campaign_goal="Educate on winter volume and drive sales for end-of-month promo (30% off)",
        duration="January 2026",
        total_emails=3,
        promotional_ratio=0.7 # 2 out of 3 is approx 0.67
    )
    
    print(f"\nPLAN OUTPUT: {plan_output}")
    
    # Extract ID
    try:
        # Format: "Campaign Plan Created! ID: <ID>. Status: ..."
        campaign_id = plan_output.split("ID: ")[1].split(".")[0]
        print(f"CAPTURED ID: {campaign_id}")
        
        # 2. Generate
        gen_output = await generate_email_campaign(campaign_id)
        print(f"\nGENERATE OUTPUT: {gen_output}")
        
    except Exception as e:
        print(f"FAILED TO PARSE ID or GENERATE: {e}")

if __name__ == "__main__":
    asyncio.run(main())
