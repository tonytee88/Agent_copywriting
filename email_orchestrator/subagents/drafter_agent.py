import json
from pathlib import Path
from typing import Dict, Any, Optional

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.schemas import EmailBlueprint, BrandBio, EmailDraft
from email_orchestrator.config import MODEL_DRAFTER

# Initialize tools
knowledge_reader = KnowledgeReader()

async def drafter_agent(
    blueprint: EmailBlueprint, 
    brand_bio: BrandBio,
    revision_feedback: Optional[str] = None,
    language: str = "French",
    campaign_context: Optional[str] = None
) -> EmailDraft:
    """
    The Drafter Agent writes the email content based on the Strategist's blueprint.
    It strictly follows the 'Type #1' format guide.
    """
    if revision_feedback:
        print(f"[Drafter] Revising email for {blueprint.brand_name} based on feedback...")
    else:
        print(f"[Drafter] Writing email for {blueprint.brand_name}...")

    # 1. Fetch Context
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
        brand_bio=brand_bio.model_dump_json(indent=2),
        revision_feedback=revision_feedback or "N/A - First draft"
    )
    
    # Inject Language Instruction
    full_prompt += f"\n\nCRITICAL: You MUST write the email in {language}."
    
    # Inject Campaign Context (User Constraints)
    if campaign_context:
        full_prompt += f"\n\nCAMPAIGN CONTEXT/CONSTRAINTS:\n{campaign_context}\n\nIMPORTANT: You MUST respect all constraints mentioned in the Campaign Context above."
    
    # Inject Campaign Context (User Constraints)
    if campaign_context:
        full_prompt += f"\n\nCAMPAIGN CONTEXT/CONSTRAINTS:\n{campaign_context}\n\nIMPORTANT: You MUST respect all constraints mentioned in the Campaign Context above."
    
    # 4. Call Straico API
    client = get_client()
    model = MODEL_DRAFTER 
    
    print(f"[Drafter] Sending prompt to Straico...")
    result_json_str = await client.generate_text(full_prompt, model=model)
    
    # 5. Parse & Validate
    return _parse_draft_response(result_json_str)

class DraftingSession:
    """
    Manages a stateful drafting session for a single email slot.
    Maintains context across revision loops (Draft -> Verify -> Revise).
    """
    def __init__(self, blueprint: EmailBlueprint, brand_bio: BrandBio, language: str, campaign_context: Optional[str] = None):
        self.blueprint = blueprint
        self.brand_bio = brand_bio
        self.language = language
        self.campaign_context = campaign_context
        self.history = [] # List of {"role": "user"|"assistant", "content": str}
        self.client = get_client()
        self.model = MODEL_DRAFTER
        self.knowledge_reader = KnowledgeReader()

    async def start(self) -> EmailDraft:
        """Generates the initial draft."""
        print(f"[DraftingSession] Starting new session for {self.blueprint.brand_name}...")
        
        # 1. Fetch Context
        format_guide = self.knowledge_reader.get_document_content("Email instructions type #1.pdf")
        if not format_guide:
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
            blueprint=self.blueprint.model_dump_json(indent=2),
            brand_bio=self.brand_bio.model_dump_json(indent=2),
            revision_feedback="N/A - First draft"
        )
        
        # Inject Language & Context
        full_prompt += f"\n\nCRITICAL: You MUST write the email in {self.language}."
        if self.campaign_context:
            full_prompt += f"\n\nCAMPAIGN CONTEXT/CONSTRAINTS:\n{self.campaign_context}\n\nIMPORTANT: You MUST respect all constraints mentioned in the Campaign Context above."
            
        # 4. Execute
        self.history.append({"role": "user", "content": full_prompt})
        
        # Note: Straico tools might not support full message history in one call unless we concat.
        # For simple LLM APIs, we often concat history. 
        # Here we simulated session by appending previous turns if the API supports it, or just concat.
        # Since 'generate_text' takes a string prompt, we'll concat for now or implement chat interface if available.
        # StraicoTool.generate_text is stateless. We must manually standard prompt construction.
        
        # CONCAT STRATEGY for Stateless API:
        # We only send the system/user prompt. For revisions, we'll append history.
        # Actually proper chat persistence requires a Chat API. 
        # If StraicoTool only has 'generate_text', we simulate by appending.
        
        response_text = await self.client.generate_text(full_prompt, model=self.model)
        self.history.append({"role": "assistant", "content": response_text})
        
        return _parse_draft_response(response_text)

    async def revise(self, feedback: str) -> EmailDraft:
        # OPTIMIZED REVISION (Slim Strategy)
        # Instead of reloading the massive PDF + Blueprint, we use a targeted "Fixer" prompt.
        
        prompt_path = Path(__file__).parent.parent / "prompts" / "drafter" / "v2_revision.txt"
        try:
            prompt_template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            # Fallback (Should not happen if deployed correctly)
            print("[Drafter] Warning: v2_revision.txt not found. Using legacy revision.")
            return await self._legacy_revise(feedback)

        # Get the previous draft content
        # History structure: [User(Prompt), Assistant(Draft), User(Feedback), Assistant(Draft)...]
        # We need the LAST assistant message.
        last_draft_content = ""
        for msg in reversed(self.history):
            if msg["role"] == "assistant":
                last_draft_content = msg["content"]
                break
        
        if not last_draft_content:
            print("[Drafter] Error: No previous draft found in history.")
            return await self._legacy_revise(feedback)
            
        combined_prompt = prompt_template.format(
            last_draft=last_draft_content,
            feedback=feedback,
            language=self.language,
            brand_voice=self.brand_bio.brand_voice,
            campaign_context=self.campaign_context or "None"
        )
        
        response_text = await self.client.generate_text(combined_prompt, model=self.model)
        
        # Append to history for continuity (though we skipped the full context in this turn)
        self.history.append({"role": "user", "content": f"Feedback: {feedback}"})
        self.history.append({"role": "assistant", "content": response_text})
        
        return _parse_draft_response(response_text)

    async def _legacy_revise(self, feedback: str) -> EmailDraft:
        """Legacy revision method (Backup)."""
        # ... (Original Logic if needed, or just fail)
        # For now, just simplistic fallback or raising error
        pass



def _parse_draft_response(result_json_str: str) -> EmailDraft:
    """Shared parsing logic."""
    try:
        cleaned_json = _clean_json_string(result_json_str)
        data = json.loads(cleaned_json)
        
        # Helper to construct full formatted text for email preview
        full_text = _construct_full_email_text(data)
        data["full_text_formatted"] = full_text
        
        draft = EmailDraft(**data)
        
        print(f"[Drafter] Draft created: {draft.subject}")
        return draft
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[Drafter] Error parsing JSON: {e}")
        print(f"[Drafter] Raw output: {result_json_str[:500]}...")
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

def _construct_full_email_text(data: Dict[str, Any]) -> str:
    """Helper to assemble the email parts into a readable string."""
    products_list = "\n".join([f"- {p}" for p in data.get('products', [])])
    if not products_list and data.get('product_block_content'):
        products_list = data.get('product_block_content')

    return f"""
SUBJECT: {data.get('subject')}
PREVIEW: {data.get('preview')}
HERO IMAGE: {data.get('hero_image_description')}
HERO TITLE: {data.get('hero_title')}
HERO SUBTITLE: {data.get('hero_subtitle')}
CTA: {data.get('hero_cta_text')}

--- DESCRIPTIVE BLOCK ---
TITLE: {data.get('descriptive_block_title')}
CONTENT: {data.get('descriptive_block_content')}
CTA DESCRIPTIVE: {data.get('cta_descriptive', 'N/A')}

--- PRODUCTS ---
{products_list}
CTA: {data.get('product_block_cta_text')}

--- FOOTER ---
{data.get('footer_text')}
"""


