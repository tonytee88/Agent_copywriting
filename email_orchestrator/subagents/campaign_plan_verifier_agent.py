import json
from pathlib import Path
from typing import List

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.schemas import BrandBio, CampaignPlan, CampaignPlanVerification

# Initialize tools
history_manager = HistoryManager()

async def campaign_plan_verifier_agent(
    plan: CampaignPlan,
    brand_bio: BrandBio
) -> CampaignPlanVerification:
    """
    Verifies campaign plan quality and strategic coherence.
    
    Checks:
    - Variety: No transformation/angle/structure used more than once
    - Balance: Promotional ratio matches target
    - Coherence: Logical progression and connections
    - Momentum: Educational content supports promotional goals
    
    Args:
        plan: The campaign plan to verify
        brand_bio: Brand context
    
    Returns:
        CampaignPlanVerification with approval status and feedback
    """
    print(f"[Campaign Plan Verifier] Verifying plan: {plan.campaign_name}...")
    
    # 1. Fetch History
    recent_history = history_manager.get_recent_campaigns(plan.brand_name, limit=20)
    history_summary = _format_history_for_verifier(recent_history)
    
    # 2. Load Prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "campaign_plan_verifier" / "v1.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Campaign Plan Verifier prompt v1.txt not found")
    
    # 3. Format Prompt
    full_prompt = prompt_template.format(
        campaign_plan=plan.model_dump_json(indent=2),
        brand_bio=brand_bio.model_dump_json(indent=2),
        history_log=history_summary
    )
    
    # 4. Call Straico API
    client = get_client()
    model = "openai/gpt-4o-2024-11-20"
    
    print(f"[Campaign Plan Verifier] Sending prompt to Straico...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse
    try:
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        result = CampaignPlanVerification(**data)
        
        if result.approved:
            print(f"[Campaign Plan Verifier] APPROVED (Score: {result.score}/10)")
        else:
            print(f"[Campaign Plan Verifier] REJECTED. Issues: {result.critical_issues}")
            
        return result
        
    except Exception as e:
        print(f"[Campaign Plan Verifier] EXCEPTION: {e}")
        print(f"[Campaign Plan Verifier] RAW OUTPUT: {result_json_str[:500]}...")
        
        # Return a failed verification
        return CampaignPlanVerification(
            approved=False,
            score=0,
            variety_check={
                "no_repeated_transformations": False,
                "no_repeated_angles": False,
                "no_repeated_structures": False,
                "no_recent_history_conflicts": False
            },
            balance_check={
                "promotional_ratio_ok": False,
                "no_excessive_consecutive_hard_sells": False,
                "educational_placement_strategic": False
            },
            coherence_check={
                "logical_flow": False,
                "smooth_transitions": False,
                "momentum_builds": False,
                "educational_supports_promotional": False
            },
            critical_issues=[f"System Exception: {e}"],
            suggestions=[],
            feedback_for_planner="System error in verification. Please try again."
        )

def _format_history_for_verifier(history: List[CampaignLogEntry]) -> str:
    """Format history for verification prompt."""
    if not history:
        return "No history."
    
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
        text = text[start:end]
    
    return text
