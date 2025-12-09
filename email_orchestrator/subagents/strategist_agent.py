import json
from pathlib import Path
from typing import Dict, Any, List
import traceback

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.schemas import CampaignRequest, BrandBio, EmailBlueprint

# Initialize tools
knowledge_reader = KnowledgeReader()
history_manager = HistoryManager()

async def strategist_agent(
    request: CampaignRequest, 
    brand_bio: BrandBio
) -> EmailBlueprint:
    """
    The Strategist Agent plans the email campaign structure and angle.
    It reads the Knowledge Base (PDFs) and History Log to make informed decisions.
    
    Args:
        request: The user's campaign request.
        brand_bio: The brand's context.
        
    Returns:
        A structured EmailBlueprint Pydantic model.
    """
    print(f"[Strategist] Planning campaign for {request.brand_name}...")

    # 1. Fetch Context
    # Get knowledge base text (cached)
    kb_text = knowledge_reader.get_all_context()
    
    # Get recent history for this brand
    recent_history = history_manager.get_recent_campaigns(request.brand_name, limit=10)
    history_summary = _format_history_for_prompt(recent_history)
    
    # 2. Load Prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "strategist" / "v1.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Strategist prompt v1.txt not found")
    
    # 3. Format Prompt
    full_prompt = prompt_template.format(
        campaign_request=request.model_dump_json(indent=2),
        brand_bio=brand_bio.model_dump_json(indent=2),
        history_log=history_summary,
        knowledge_base=kb_text
    )
    
    # 4. Call Straico API
    # Using GPT-4o or similar high-reasoning model via Straico
    client = get_client()
    # Note: Using a model capable of handling large context (PDFs)
    model = "openai/gpt-4o-2024-11-20" 
    
    print(f"[Strategist] Sending prompt to Straico (approx {len(full_prompt)} chars)...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse & Validate
    try:
        # Improve JSON cleaning logic
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        
        # Ensure it matches schema
        blueprint = EmailBlueprint(**data)
        
        print(f"[Strategist] Blueprint created: {blueprint.descriptive_structure_name} / {blueprint.storytelling_angle}")
        return blueprint
        
    except Exception as e:
        print(f"[Strategist] EXCEPTION: {e}")
        print(f"[Strategist] TRACEBACK: {traceback.format_exc()}")
        print(f"[Strategist] RAW JSON STRING: {result_json_str}")
        try:
            print(f"[Strategist] PARSED DATA: {json.loads(_clean_json_string(result_json_str))}")
        except:
            pass
        raise e

def _format_history_for_prompt(history: List[CampaignLogEntry]) -> str:
    """Helper to create a concise summary of past emails for the prompt."""
    if not history:
        return "No previous emails found."
        
    summary_lines = []
    for i, entry in enumerate(history):
        line = (
            f"Email #{i+1} ({entry.timestamp}): "
            f"Transformation='{entry.transformation_used}', "
            f"Structure='{entry.structure_used}', "
            f"Angle='{entry.storytelling_angle_used}'"
        )
        summary_lines.append(line)
        
    return "\n".join(summary_lines)

def _clean_json_string(raw_text: str) -> str:
    """aggressive json cleanup"""
    text = raw_text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
        
    text = text.strip()
    
    # Sometimes models output text before the JSON object
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        text = text[start:end]
        
    return text
