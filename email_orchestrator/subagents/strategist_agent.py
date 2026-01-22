import json
from pathlib import Path
from typing import Dict, Any, List
import traceback

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.tools.catalog_manager import get_catalog_manager
from email_orchestrator.schemas import CampaignRequest, BrandBio, EmailBlueprint
from email_orchestrator.config import MODEL_STRATEGIST

# Initialize tools
history_manager = HistoryManager()

async def strategist_agent(
    request: CampaignRequest, 
    brand_bio: BrandBio,
    campaign_context: Any = None,
    language: str = "French"
) -> EmailBlueprint:
    """
    The Strategist Agent plans the email campaign structure and angle using Catalog IDs.
    """
    print(f"[Strategist] Planning campaign for {request.brand_name}...")
    
    # 1. Load Catalogs (Structures Only - others are free text directives)
    cm = get_catalog_manager()
    catalogs_data = {
        "structures": cm.get_global_catalog("structures"),
    }
    catalogs_str = json.dumps(catalogs_data, indent=2)

    # 2. Get recent history for this brand
    recent_history = history_manager.get_recent_campaigns(request.brand_name, limit=5)
    history_summary = _format_history_for_prompt(recent_history)
    
    # 3. Load Prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "strategist" / "v1.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Strategist prompt v1.txt not found")
    
    # 4. Format Directives (if coming from Planner)
    campaign_directives = ""
    start_str = ""
    if campaign_context:
        # Accessing description fields from EmailSlot
        cta = campaign_context.cta_description or "Decide based on intensity"
        campaign_directives = f"""
=== ASSIGNED DIRECTIVES (FROM PLANNER) ===
You MUST use these specific Creative Directives assigned by the Campaign Planner:
- Transformation Arc: {campaign_context.transformation_description}
- Angle/Hook: {campaign_context.angle_description}
- Structure ID: {campaign_context.structure_id}
- Persona Voice: {campaign_context.persona_description}
- CTA Style: {cta}

Context:
- Theme: {campaign_context.theme}
- Key Message: {campaign_context.key_message}
- Purpose: {campaign_context.email_purpose}
- Intensity: {campaign_context.intensity_level}
- Target Language: {language} (You MUST write the blueprint content in this language)
"""
    
    full_prompt = prompt_template.format(
        campaign_request=request.model_dump_json(indent=2),
        brand_bio=brand_bio.model_dump_json(indent=2),
        history_log=history_summary,
        catalogs=catalogs_str,
        campaign_directives=campaign_directives
    )
    
    # Inject Feedback
    if brand_bio.feedback_notes:
        feedback_list = "\n".join([f"- {note}" for note in brand_bio.feedback_notes])
        feedback_section = f"""
=== CRITICAL CLIENT FEEDBACK ===
The client has provided specific feedback. You MUST prioritize these notes over general best practices:
{feedback_list}
================================
"""
        full_prompt = feedback_section + "\n\n" + full_prompt
    
    # 5. Call Straico API
    client = get_client()
    model = MODEL_STRATEGIST 
    
    print(f"[Strategist] Sending prompt to Straico...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 6. Parse & Validate
    try:
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        
        # Ensure brand_name is set
        if "brand_name" not in data:
            data["brand_name"] = request.brand_name
            
        blueprint = EmailBlueprint(**data)
        
        print(f"[Strategist] Blueprint created. Structure: {blueprint.structure_id}")
        return blueprint
        
    except Exception as e:
        print(f"[Strategist] EXCEPTION: {e}")
        print(f"[Strategist] RAW JSON: {result_json_str}")
        raise e

def _format_history_for_prompt(history: List[CampaignLogEntry]) -> str:
    """Helper to create a concise summary of past emails for the prompt."""
    if not history:
        return "No previous emails found."
        
    summary_lines = []
    for i, entry in enumerate(history):
        # Handle graceful fallback if fields missing in old logs
        trans = getattr(entry, 'transformation_description', None) or getattr(entry, 'transformation_id', 'Unknown')
        angle = getattr(entry, 'angle_description', None) or getattr(entry, 'angle_id', 'Unknown')
        
        line = (
            f"Email #{i+1} ({entry.timestamp}): "
            f"Trans='{trans}', "
            f"Struct='{entry.structure_id}', "
            f"Angle='{angle}'"
        )
        summary_lines.append(line)
        
    return "\n".join(summary_lines)

def _clean_json_string(raw_text: str) -> str:
    """aggressive json cleanup"""
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
