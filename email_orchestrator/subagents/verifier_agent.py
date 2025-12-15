import json
from pathlib import Path
from typing import Dict, Any, Tuple

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager, CampaignLogEntry
from email_orchestrator.schemas import EmailBlueprint, EmailDraft, EmailVerification
from email_orchestrator.config import STRAICO_MODEL

# Initialize tools
knowledge_reader = KnowledgeReader()
history_manager = HistoryManager()

async def verifier_agent(
    draft: EmailDraft,
    blueprint: EmailBlueprint,
    brand_name: str
) -> EmailVerification:
    """
    The Verifier Agent checks the draft for quality and adherence to rules.
    Provide actionable 'replacement_options' for easy fixing.
    """
    print(f"[Verifier] Q/A Checking email for {brand_name}...")

    # 1. Fetch Context
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=3)
    history_summary = _format_history_for_verifier(recent_history)
    
    format_rules = knowledge_reader.get_document_content("Email instructions type #1.pdf")
    if not format_rules:
        format_rules = "Adhere to Type #1 visual structure."
    
    # 2. Load Prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "verifier" / "v2.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Verifier prompt v2.txt not found")
    
    # 3. Format Prompt
    full_prompt = prompt_template.format(
        format_rules=format_rules,
        blueprint=blueprint.model_dump_json(indent=2),
        history_log=history_summary,
        draft=draft.model_dump_json(indent=2)
    )
    
    # 4. Call Straico API
    client = get_client()
    model = STRAICO_MODEL
    
    print(f"[Verifier] Sending prompt to Straico...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse
    try:
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        result = EmailVerification(**data)
        
        if result.approved:
            print(f"[Verifier] APPROVED (Score: {result.score}/10)")
        else:
            print(f"[Verifier] REJECTED. Issues: {len(result.issues)}")
            for issue in result.issues:
                print(f" - [{issue.severity}] {issue.problem} ({issue.field})")
            
            print(f"\n[Verifier] Feedback: {result.feedback_for_drafter}")
            
            if result.replacement_options:
                ro = result.replacement_options
                print(f"[Verifier] Replacement Options Suggest:")
                if ro.subject_alternatives:
                    print(f" - Subject Lines: {ro.subject_alternatives}")
                if ro.preview_alternatives:
                    print(f" - Preview Text: {ro.preview_alternatives}")
                if ro.hero_title_alternatives:
                    print(f" - Hero Titles: {ro.hero_title_alternatives}")
                if ro.hero_subtitle_alternatives:
                    print(f" - Hero Subtitles: {ro.hero_subtitle_alternatives}")
                if ro.hero_cta_alternatives:
                    print(f" - Hero CTAs: {ro.hero_cta_alternatives}")
                if ro.product_cta_alternatives:
                    print(f" - Product CTAs: {ro.product_cta_alternatives}")
                if ro.descriptive_block_rewrite_hint:
                    print(f" - Rewrite Hint: {ro.descriptive_block_rewrite_hint}")

        return result
        
    except Exception as e:
        print(f"[Verifier] EXCEPTION: {e}")
        print(f"[Verifier] RAW OUTPUT: {result_json_str}")
        
        # Fallback
        return EmailVerification(
            approved=False, 
            score=0, 
            critical_issues=[f"System Exception: {e}"], 
            feedback_for_drafter="System error in verification.",
            issues=[],
            replacement_options=None
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
        return text[start:end]
    return text

def _format_history_for_verifier(history: list[CampaignLogEntry]) -> str:
    if not history:
        return "No history."
    # We might want to include subject lines here to check for copy repetition
    return "\n".join([f"Email {i}: Trans={e.transformation_id}, Struct={e.structure_id}, Subject='{getattr(e.final_draft, 'subject', 'N/A')}'" for i, e in enumerate(history)])
