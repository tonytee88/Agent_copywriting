"""
Campaign Planner Agent - ADK/Gemini Implementation
Uses tool calling for strategic content selection.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from google.adk.agents.llm_agent import Agent
from email_orchestrator.schemas import BrandBio, CampaignPlan
from email_orchestrator.tools.timing_calculator import calculate_send_schedule, parse_duration_to_start_date
from email_orchestrator.tools.history_manager import HistoryManager
from email_orchestrator.tools.campaign_planner_tools import (
    get_transformation_options,
    get_storytelling_angle_options,
    get_structure_options,
    get_persona_options,
    validate_campaign_variety
)

# Initialize history manager
history_manager = HistoryManager()

def load_campaign_planner_instruction() -> str:
    """Load the campaign planner prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "campaign_planner" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")

# Create the Campaign Planner ADK Agent
campaign_planner_adk_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="campaign_planner",
    description="Strategic multi-email campaign planner with tool access for content selection",
    instruction=load_campaign_planner_instruction(),
    tools=[
        get_transformation_options,
        get_storytelling_angle_options,
        get_structure_options,
        get_persona_options,
        validate_campaign_variety
    ]
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
    Plans a multi-email campaign using ADK agent with tool access.
    
    Args:
        brand_name: Name of the brand
        campaign_goal: High-level objective
        total_emails: Number of emails to plan
        duration: Campaign duration (e.g., "1 month", "next month")
        brand_bio: Brand context
        promotional_ratio: Ratio of promotional emails (0.0-1.0)
    
    Returns:
        CampaignPlan with all email slots defined
    """
    print(f"[Campaign Planner ADK] Planning {total_emails}-email campaign for {brand_name}...")
    
    # 1. Calculate send schedule (rule-based)
    start_date = parse_duration_to_start_date(duration)
    send_schedule = calculate_send_schedule(start_date, total_emails, duration)
    
    # Format schedule for prompt
    schedule_str = json.dumps(send_schedule, indent=2)
    
    # 2. Get historic campaigns for context
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=20)
    history_summary = _format_history_for_prompt(recent_history)
    
    # 3. Prepare prompt variables
    promotional_percentage = int(promotional_ratio * 100)
    educational_percentage = 100 - promotional_percentage
    
    prompt_vars = {
        "brand_name": brand_name,
        "campaign_goal": campaign_goal,
        "total_emails": total_emails,
        "duration": duration,
        "promotional_ratio": f"{promotional_percentage}% promotional, {educational_percentage}% educational",
        "send_schedule": schedule_str,
        "brand_bio": brand_bio.model_dump_json(indent=2),
        "history_log": history_summary
    }
    
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

Historic Campaigns (Last 20 emails):
{history_summary}

Use your tools to gather strategic options and build a cohesive campaign plan.
Ensure variety, balance, and coherence as outlined in your instructions.
Review the historic campaigns to avoid repetition and create fresh content.
"""
    
    # 4. Call the ADK agent using InMemoryRunner
    print(f"[Campaign Planner ADK] Calling agent with tools...")
    
    try:
        from google.adk.runners import InMemoryRunner
        from google.genai import types as genai_types
        
        runner = InMemoryRunner(agent=campaign_planner_adk_agent, app_name="campaign_planner")
        
        # Create session
        session = await runner.session_service.create_session(
            app_name="campaign_planner",
            user_id="campaign_planner_user"
        )
        
        # Build user message
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)]
        )
        
        # Run agent and collect response
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
        
        # Parse JSON from response
        cleaned_json = _clean_json_string(result_text)
        data = json.loads(cleaned_json)
        
        # Validate and create CampaignPlan
        plan = CampaignPlan(**data)
        
        print(f"[Campaign Planner ADK] ✓ Campaign plan created: {plan.campaign_name} ({plan.total_emails} emails)")
        return plan
        
    except Exception as e:
        print(f"[Campaign Planner ADK] ERROR: {e}")
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
    
    Args:
        original_plan: The CampaignPlan that failed verification
        verification_feedback: CampaignPlanVerification with issues and suggestions
        brand_bio: Brand context
    
    Returns:
        Revised CampaignPlan
    """
    print(f"[Campaign Planner Revision] Revising plan based on feedback...")
    
    # Build revision request
    revision_message = f"""
I need you to revise the following campaign plan based on verification feedback.

ORIGINAL PLAN:
{original_plan.model_dump_json(indent=2)}

VERIFICATION FEEDBACK:
- Score: {verification_feedback.score}/10
- Approved: {verification_feedback.approved}

CRITICAL ISSUES:
{chr(10).join(f"- {issue}" for issue in verification_feedback.critical_issues)}

SUGGESTIONS FOR IMPROVEMENT:
{chr(10).join(f"- {suggestion}" for suggestion in verification_feedback.suggestions)}

DETAILED FEEDBACK:
{verification_feedback.feedback_for_planner}

REVISION INSTRUCTIONS:
1. Keep the same campaign_id, brand_name, campaign_goal, duration, and total_emails
2. Fix ALL critical issues mentioned above
3. Implement the suggestions provided
4. Maintain variety (no repeated transformations, angles, or structures)
5. Ensure proper promotional balance
6. Keep logical flow and connections between emails
7. Return ONLY valid JSON matching the CampaignPlan schema

Please revise the plan now, addressing all issues.
"""
    
    try:
        from google.adk.runners import InMemoryRunner
        from google.genai import types as genai_types
        
        runner = InMemoryRunner(agent=campaign_planner_adk_agent, app_name="campaign_planner_revision")
        
        # Create session
        session = await runner.session_service.create_session(
            app_name="campaign_planner_revision",
            user_id="campaign_planner_user"
        )
        
        # Build user message
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=revision_message)]
        )
        
        # Run agent and collect response
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
        
        # Parse JSON from response
        cleaned_json = _clean_json_string(result_text)
        data = json.loads(cleaned_json)
        
        # Validate and create revised CampaignPlan
        revised_plan = CampaignPlan(**data)
        
        print(f"[Campaign Planner Revision] ✓ Revised plan created: {revised_plan.campaign_name}")
        return revised_plan
        
    except Exception as e:
        print(f"[Campaign Planner Revision] ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        raise e

def _clean_json_string(raw_text: str) -> str:
    """Aggressive JSON cleanup"""
    text = raw_text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
        
    text = text.strip()
    
    # Extract JSON object
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        text = text[start:end]
        
    return text

def _format_history_for_prompt(history) -> str:
    """Format history for campaign planner prompt."""
    if not history:
        return "No previous emails found."
    
    summary_lines = []
    for i, entry in enumerate(history):
        line = (
            f"Email #{i+1} ({entry.timestamp[:10]}): "
            f"Transformation='{entry.transformation_used}', "
            f"Structure='{entry.structure_used}', "
            f"Angle='{entry.storytelling_angle_used}'"
        )
        summary_lines.append(line)
    
    return "\n".join(summary_lines)
