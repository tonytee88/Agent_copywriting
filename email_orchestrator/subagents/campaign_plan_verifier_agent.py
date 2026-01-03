import json
from pathlib import Path
from typing import List

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.tools.catalog_manager import get_catalog_manager
from email_orchestrator.schemas import BrandBio, CampaignPlan, CampaignPlanVerification, BlockingIssue
from email_orchestrator.schemas import BrandBio, CampaignPlan, CampaignPlanVerification, BlockingIssue
from email_orchestrator.config import MODEL_VERIFIER

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
    
    # 0. Load Catalogs (Structures Only)
    cm = get_catalog_manager()
    catalogs_data = {
        "structures": cm.get_global_catalog("structures"),
    }
    catalogs_str = json.dumps(catalogs_data, indent=2)

    # 1. Fetch History
    recent_history = history_manager.get_recent_campaigns(plan.brand_name, limit=3)
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
    client = get_client()
    model = MODEL_VERIFIER
    
    print(f"[Campaign Plan Verifier] Sending prompt to Straico...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse
    try:
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        result = CampaignPlanVerification(**data)
        
        if result.approved:
            print(f"[Campaign Plan Verifier] ✅ APPROVED: {result.final_verdict}")
        else:
            print(f"[Campaign Plan Verifier] ❌ REJECTED: {result.final_verdict}")
            print(f"Top Improvements Needed: {len(result.top_improvements)}")
            for imp in result.top_improvements:
                print(f" - [{imp.category}] {imp.problem}")
                print(f"   Rationale: {imp.why_it_matters}")
                for key, val in imp.options.items():
                    print(f"   Option {key}: {val}")
        
        return result
        
    except Exception as e:
        print(f"[Campaign Plan Verifier] EXCEPTION: {e}")
        print(f"[Campaign Plan Verifier] RAW OUTPUT: {result_json_str}")
        
        # Return a failed verification with the new schema in mind
        return CampaignPlanVerification(
            approved=False,
            final_verdict=f"System error in verification: {e}",
            blocking_issues=[
                BlockingIssue(
                    category="calendar_sanity", 
                    description="Verification agent failed to parse LLM response.",
                    why_it_matters="Technical failure prevents strategic verification."
                )
            ],
            optimization_options=[]
        )

def _format_history_for_verifier(history: List[CampaignLogEntry]) -> str:
    """Format history for verification prompt (Descriptions)."""
    if not history:
        return "No history."
    
    summary_lines = []
    for i, entry in enumerate(history):
        # Handle mixed history (IDs vs Descriptions) gracefully knowing schemas.py has description fields now
        # Accessing raw dict might be safer if objects were loaded from old JSON, 
        # but Pydantic load would have mapped them if aliases were set.
        # Since I just replaced fields, old history might break loading if fields are missing.
        # Assuming history manager handles loading or returns defaults.
        # Ideally, we map: transformation_id (old) -> transformation_description (new)
        
        trans = getattr(entry, 'transformation_description', None) or getattr(entry, 'transformation_id', 'Unknown')
        angle = getattr(entry, 'angle_description', None) or getattr(entry, 'angle_id', 'Unknown')
        struct = entry.structure_id
        
        line = (
            f"Email #{i+1} ({entry.timestamp[:10]}): "
            f"Trans='{trans}', "
            f"Struct='{struct}', "
            f"Angle='{angle}'"
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
    text = text.replace('"why_it.matters"', '"why_it_matters"')
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        return text[start:end]
    return text
