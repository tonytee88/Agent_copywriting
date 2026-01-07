
import json
from typing import Optional
from email_orchestrator.tools.straico_tool import StraicoAPIClient
from email_orchestrator.schemas import EmailDraft

class TranslatorAgent:
    """
    Specialized agent for Transcreation (Creative Translation).
    Converts a primary draft (e.g. FR) into a target language (e.g. EN)
    maintaining the exact structure, tone, and intent, but adapting for native nuance.
    """
    
    def __init__(self):
        self.client = StraicoAPIClient()
        self.model = "openai/gpt-4o-mini" # Fast & Good at translation

    async def transcreate_draft(self, source_draft: EmailDraft, source_lang: str, target_lang: str, brand_voice: str) -> EmailDraft:
        """
        Takes a full EmailDraft and returns a new EmailDraft with all text fields transcreated.
        """
        print(f"[Translator] Transcreating draft from {source_lang} to {target_lang}...")
        
        # Serialize source for context
        source_json = source_draft.model_dump_json(indent=2)
        
        prompt = f"""
You are an expert **Bilingual Copywriter & Transcreator**.
Your task is to take an email draft written in **{source_lang}** and adapt it into **{target_lang}**.

### GOAL
Do NOT just translate literally. You must **TRANSCREATE**:
1.  **Maintain the Structure**: The resulting JSON must have the EXACT same keys.
2.  **Adapt the Tone**: Ensure it sounds like a **Native Speaker** of {target_lang} wrote it, matching the Brand Voice: "{brand_voice}".
3.  **Preserve Intent**: The benefits, offers, and emotional hooks must remain the same.

### SOURCE DRAFT ({source_lang}):
{source_json}

### INSTRUCTIONS
Return a JSON object matching the `EmailDraft` schema exactly, but with all text values (subject, preview, hero_title, body content, CTAs, etc.) translated/adapted into {target_lang}.
Keep technical IDs (transformation_id, structure_id, etc.) UNCHANGED.

### STRICT OUTPUT FORMAT
Return ONLY valid JSON.
"""
        
        try:
            response = await self.client.generate_text(prompt, model=self.model)
            cleaned = self._clean_json(response)
            data = json.loads(cleaned)
            
            # Reconstruct Draft object
            new_draft = EmailDraft(**data)
            
            # Construct full text for preview
            # (We need to re-run the format helper, or just trust the new draft has text)
            # The prompt asks for fields, and EmailDraft has a field 'full_text_formatted'.
            # The LLM might hallucinate this field or strip it. It's safer to reconstruct it.
            # Reconstruct Draft object
            new_draft = EmailDraft(**data)
            new_draft.full_text_formatted = new_draft.to_formatted_text()

            return new_draft
            
        except Exception as e:
            print(f"[Translator] Error transcreating: {e}")
            raise e

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()
