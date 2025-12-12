import json
from pathlib import Path
from typing import List

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.tools.catalog_manager import get_catalog_manager
from email_orchestrator.schemas import BrandBio, CampaignPlan, CampaignPlanVerification

# Initialize tools
history_manager = HistoryManager()

async def campaign_plan_verifier_agent(
    plan: CampaignPlan,
    brand_bio: BrandBio
) -> CampaignPlanVerification:
    """
    Verifies campaign plan quality using 'Judge + Repair' logic.
    Provides structured feedback and ID replacements.
    """
    print(f"[Campaign Plan Verifier] Verifying plan: {plan.campaign_name}...")
    
    # 0. Load Catalogs (to validate IDs and suggest repairs)
    cm = get_catalog_manager()
    catalogs_data = {
        "structures": cm.get_global_catalog("structures"),
        "angles": cm.get_global_catalog("angles"),
        "cta_styles": cm.get_global_catalog("cta_styles"),
        "personas": cm.get_brand_catalog(plan.brand_name, "personas"),
        "transformations": cm.get_brand_catalog(plan.brand_name, "transformations")
    }
    catalogs_str = json.dumps(catalogs_data, indent=2)

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
        history_log=history_summary,
        catalogs=catalogs_str
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
            issue_count = len(result.issues)
            print(f"[Campaign Plan Verifier] REJECTED. {issue_count} issues found.")
            for issue in result.issues:
                print(f" - [{issue.severity}] {issue.problem}")
            
        return result
        
    except Exception as e:
        print(f"[Campaign Plan Verifier] EXCEPTION: {e}")
        print(f"[Campaign Plan Verifier] RAW OUTPUT: {result_json_str[:500]}...")
        
        # Return a failed verification
        return CampaignPlanVerification(
            approved=False,
            score=0,
            variety_check={},
            balance_check={},
            coherence_check={},
            critical_issues=[f"System Exception: {e}"],
            issues=[],
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
            f"Transformation='{entry.transformation_id}', "
            f"Structure='{entry.structure_id}', "
            f"Angle='{entry.angle_id}'"
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
        return text[start:end]
    return text
