"""
Campaign Planner Agent - ADK/Gemini Implementation
Uses Catalog Injection for strategic content selection.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from google.adk.agents.llm_agent import Agent
from email_orchestrator.schemas import BrandBio, CampaignPlan
from email_orchestrator.tools.timing_calculator import calculate_send_schedule, parse_duration_to_start_date
from email_orchestrator.tools.history_manager import HistoryManager
from email_orchestrator.tools.catalog_manager import get_catalog_manager

# Initialize history manager
history_manager = HistoryManager()

def load_campaign_planner_instruction() -> str:
    """Load the campaign planner prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "campaign_planner" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")

# Create the Campaign Planner ADK Agent (No tools needed with Catalog Injection)
campaign_planner_adk_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="campaign_planner",
    description="Strategic multi-email campaign planner using Catalog Injection",
    instruction=load_campaign_planner_instruction(),
    tools=[] # No tools needed, catalogs are provided in context
)

async def campaign_planner_agent(
    brand_name: str,
    campaign_goal: str,
    total_emails: int,
    duration: str,
    brand_bio: BrandBio,
    promotional_ratio: float = 0.4
) -> CampaignPlan:
    """
    Plans a multi-email campaign using ADK agent with Catalog Injection.
    """
    print(f"[Campaign Planner] Planning {total_emails}-email campaign for {brand_name}...")
    
    # 0. Load Catalogs
    cm = get_catalog_manager()
    catalogs_data = {
        "structures": cm.get_global_catalog("structures"),
        "angles": cm.get_global_catalog("angles"),
        "cta_styles": cm.get_global_catalog("cta_styles"),
        "personas": cm.get_brand_catalog(brand_name, "personas"),
        "transformations": cm.get_brand_catalog(brand_name, "transformations")
    }
    catalogs_str = json.dumps(catalogs_data, indent=2)
    
    # 1. Calculate send schedule
    start_date = parse_duration_to_start_date(duration)
    send_schedule = calculate_send_schedule(start_date, total_emails, duration)
    schedule_str = json.dumps(send_schedule, indent=2)
    
    # 2. Get historic campaigns
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=20)
    history_summary = _format_history_for_prompt(recent_history)
    
    # 3. Prepare prompt variables
    promotional_percentage = int(promotional_ratio * 100)
    educational_percentage = 100 - promotional_percentage
    
    # 4. Build the user message
    user_message = f"""
Please create a campaign plan with the following requirements:

Brand: {brand_name}
Goal: {campaign_goal}
Total Emails: {total_emails}
Duration: {duration}
Promotional Ratio: {promotional_percentage}% promotional, {educational_percentage}% educational

Send Schedule (pre-calculated):
{schedule_str}

Brand Bio:
{brand_bio.model_dump_json(indent=2)}

=== CATALOGS (AVAILABLE IDs) ===
{catalogs_str}
================================

Historic Campaigns (AVOID REPEATING THESE IDs):
{history_summary}

Requirements:
1. Select valid IDs from the [CATALOGS] for every strategic field.
2. Ensure variety (no repeated IDs within this campaign).
3. Ensure logical flow and balance.
"""
    
    # 5. Call the ADK agent
    try:
        from google.adk.runners import InMemoryRunner
        from google.genai import types as genai_types
        
        runner = InMemoryRunner(agent=campaign_planner_adk_agent, app_name="campaign_planner")
        session = await runner.session_service.create_session(
            app_name="campaign_planner",
            user_id="campaign_planner_user"
        )
        
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)]
        )
        
        result_text = ""
        async for event in runner.run_async(
            user_id="campaign_planner_user",
            session_id=session.id,
            new_message=user_content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result_text += part.text
        
        cleaned_json = _clean_json_string(result_text)
        data = json.loads(cleaned_json)
        
        # Ensure created_at is present
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
            
        plan = CampaignPlan(**data)
        print(f"[Campaign Planner] ✓ Plan created: {plan.campaign_name} ({plan.total_emails} emails)")
        return plan
        
    except Exception as e:
        print(f"[Campaign Planner] ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        raise e

async def revise_campaign_plan(
    original_plan,
    verification_feedback,
    brand_bio: BrandBio
) -> "CampaignPlan":
    """
    Revises a campaign plan based on verification feedback.
    """
    print(f"[Campaign Planner Revision] Revising plan based on feedback...")
    
    # Re-load catalogs for revision context
    cm = get_catalog_manager()
    catalogs_data = {
        "structures": cm.get_global_catalog("structures"),
        "angles": cm.get_global_catalog("angles"),
        "cta_styles": cm.get_global_catalog("cta_styles"),
        "personas": cm.get_brand_catalog(original_plan.brand_name, "personas"),
        "transformations": cm.get_brand_catalog(original_plan.brand_name, "transformations")
    }
    catalogs_str = json.dumps(catalogs_data, indent=2)
    
    revision_message = f"""
I need you to revise the following campaign plan based on verification feedback.

ORIGINAL PLAN:
{original_plan.model_dump_json(indent=2)}

=== CATALOGS (VALID IDs) ===
{catalogs_str}
============================

VERIFICATION FEEDBACK:
- Score: {verification_feedback.score}/10
- Approved: {verification_feedback.approved}

CRITICAL ISSUES:
{chr(10).join(f"- {issue.problem}" for issue in verification_feedback.issues)}

SUGGESTED REPAIRS (USE THESE IDs!):
{json.dumps([s.model_dump() for s in verification_feedback.per_email_suggestions], indent=2)}

DETAILED FEEDBACK:
{verification_feedback.feedback_for_planner}

REVISION RULES:
1. Fix ALL critical issues.
2. If specific IDs were suggested in 'per_email_suggestions', YOU MUST USE THEM.
3. Return ONLY valid JSON matching the CampaignPlan schema.
"""
    
    try:
        from google.adk.runners import InMemoryRunner
        from google.genai import types as genai_types
        
        runner = InMemoryRunner(agent=campaign_planner_adk_agent, app_name="campaign_planner_revision")
        session = await runner.session_service.create_session(
            app_name="campaign_planner_revision",
            user_id="campaign_planner_user"
        )
        
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=revision_message)]
        )
        
        result_text = ""
        async for event in runner.run_async(
            user_id="campaign_planner_user",
            session_id=session.id,
            new_message=user_content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result_text += part.text
        
        cleaned_json = _clean_json_string(result_text)
        data = json.loads(cleaned_json)
        revised_plan = CampaignPlan(**data)
        
        print(f"[Campaign Planner Revision] ✓ Revised plan created")
        return revised_plan
        
    except Exception as e:
        print(f"[Campaign Planner Revision] ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        raise e

def _clean_json_string(raw_text: str) -> str:
    """Aggressive JSON cleanup"""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        return text[start:end]
    return text

def _format_history_for_prompt(history) -> str:
    """Format history for campaign planner prompt."""
    if not history:
        return "No previous emails found."
    
    summary_lines = []
    for i, entry in enumerate(history):
        line = (
            f"Email #{i+1} ({entry.timestamp[:10]}): "
            f"Trans={entry.transformation_id}, "
            f"Struct={entry.structure_id}, "
            f"Angle={entry.angle_id}"
        )
        summary_lines.append(line)
    
    return "\n".join(summary_lines)
