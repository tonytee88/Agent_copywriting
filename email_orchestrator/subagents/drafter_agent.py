import json
from pathlib import Path
from typing import Dict, Any

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.schemas import EmailBlueprint, BrandBio, EmailDraft

# Initialize tools
knowledge_reader = KnowledgeReader()

async def drafter_agent(
    blueprint: EmailBlueprint, 
    brand_bio: BrandBio
) -> EmailDraft:
    """
    The Drafter Agent writes the email content based on the Strategist's blueprint.
    It strictly follows the 'Type #1' format guide.
    
    Args:
        blueprint: The architectural plan from the Strategist.
        brand_bio: The brand's context.
        
    Returns:
        A structured EmailDraft Pydantic model.
    """
    print(f"[Drafter] Writing email for {blueprint.brand_name}...")

    # 1. Fetch Context
    # Get format guidelines (Type #1)
    format_guide = knowledge_reader.get_document_content("Email instructions type #1.pdf")
    if not format_guide:
        print("[Drafter] Warning: 'Email instructions type #1.pdf' not found. Using minimal fallback.")
        format_guide = "Ensure strict Type #1 format: Hero, Descriptive Block, Product Block."
    
    # 2. Load Prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "drafter" / "v2.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Drafter prompt v2.txt not found")
    
    # 3. Format Prompt
    full_prompt = prompt_template.format(
        format_guide=format_guide,
        blueprint=blueprint.model_dump_json(indent=2),
        brand_bio=brand_bio.model_dump_json(indent=2)
    )
    
    # 4. Call Straico API
    client = get_client()
    # Using GPT-4o for high quality writing
    model = "openai/gpt-4o-2024-11-20" 
    
    print(f"[Drafter] Sending prompt to Straico (approx {len(full_prompt)} chars)...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse & Validate
    try:
        # Clean markdown
        result_json_str = result_json_str.strip()
        if result_json_str.startswith("```json"):
            result_json_str = result_json_str.replace("```json", "", 1)
        if result_json_str.endswith("```"):
            result_json_str = result_json_str.rstrip("`")
            
        data = json.loads(result_json_str)
        
        # Helper to construct full formatted text for email preview
        # We construct it here to ensure consistency
        full_text = _construct_full_email_text(data)
        data["full_text_formatted"] = full_text
        
        draft = EmailDraft(**data)
        
        print(f"[Drafter] Draft created: {draft.subject}")
        return draft
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[Drafter] Error parsing JSON: {e}")
        print(f"[Drafter] Raw output: {result_json_str[:500]}...")
        raise e

def _construct_full_email_text(data: Dict[str, Any]) -> str:
    """Helper to assemble the email parts into a readable string."""
    return f"""
SUBJECT: {data.get('subject')}
PREVIEW: {data.get('preview')}

=== HERO ===
Title: {data.get('hero_title')}
Subtitle: {data.get('hero_subtitle')}
CTA: {data.get('cta_hero')}

=== {data.get('descriptive_block_title')} ===
{data.get('descriptive_block_subtitle')}

{data.get('descriptive_block_content')}

=== PRODUCT ===
{data.get('product_block_content')}
CTA: {data.get('cta_product')}
"""
