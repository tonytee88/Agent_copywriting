import json
from pathlib import Path
from typing import Dict, Any, Tuple

from pydantic import BaseModel
from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.schemas import EmailBlueprint, EmailDraft

class VerificationResult(BaseModel):
    approved: bool
    critical_issues: list[str] = []
    score: int
    feedback_for_drafter: str

# Initialize tools
knowledge_reader = KnowledgeReader()
history_manager = HistoryManager()

async def verifier_agent(
    draft: EmailDraft,
    blueprint: EmailBlueprint,
    brand_name: str
) -> VerificationResult:
    """
    The Verifier Agent checks the draft for quality and adherence to rules.
    """
    print(f"[Verifier] Q/A Checking email for {brand_name}...")

    # 1. Fetch Context
    # History
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=10)
    history_summary = _format_history_for_verifier(recent_history)
    
    # Format Rules
    format_rules = knowledge_reader.get_document_content("Email instructions type #1.pdf")
    
    # 2. Load Prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "verifier" / "v1.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Verifier prompt v1.txt not found")
    
    # 3. Format Prompt
    full_prompt = prompt_template.format(
        format_rules=format_rules,
        blueprint=blueprint.model_dump_json(indent=2),
        history_log=history_summary,
        draft=draft.model_dump_json(indent=2) # We verify the JSON structure content
    )
    
    # 4. Call Straico API
    client = get_client()
    model = "openai/gpt-4o-2024-11-20"
    
    print(f"[Verifier] Sending prompt to Straico...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse
    try:

        # Improved cleanup
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        result = VerificationResult(**data)
        
        if result.approved:
            print(f"[Verifier] APPROVED (Score: {result.score}/10)")
        else:
            print(f"[Verifier] REJECTED. Issues: {result.critical_issues}")
            
        return result
        

    except Exception as e:
        print(f"[Verifier] EXCEPTION: {e}")
        print(f"[Verifier] RAW OUTPUT: {result_json_str}")
        return VerificationResult(
            approved=False, 
            score=0, 
            critical_issues=[f"System Exception: {e}"], 
            feedback_for_drafter="System error in verification."
        )

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
        text = text[start:end]
    return text

def _format_history_for_verifier(history: list[CampaignLogEntry]) -> str:
    # Similar to Strategist but maybe more focused
    if not history:
        return "No history."
    return "\n".join([f"Email {i}: Structure={e.structure_used}, Angle={e.storytelling_angle_used}" for i, e in enumerate(history)])
