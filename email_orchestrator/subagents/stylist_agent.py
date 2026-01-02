import json
import os
from typing import Dict, Any, Optional

from email_orchestrator.tools.straico_tool import StraicoAPIClient
from email_orchestrator.config import STRAICO_MODEL

class StylistAgent:
    """
    Subagent responsible for polishing and formatting the 'Descriptive Block' 
    of an email to maximize readability and conversion using tactical formatting.
    """

    def __init__(self, model: str = STRAICO_MODEL):
        self.client = StraicoAPIClient()
        self.model = model

    async def style_content(
        self, 
        content: str, 
        structure_id: str, 
        brand_voice: str, 
        language: str = "English"
    ) -> str:
        """
        Refines the raw content with pyschological formatting (Bold, Caps, Italics, Line Breaks).
        Returns valid HTML string ready for the export parser.
        """
        
        system_prompt = f"""
You are an expert **Copy Editor and Direct Response Stylist**.
Your job is to take raw email body text and transform it into a **visuallly engaging, highly readable masterpiece** using "Tactical Formatting".
You do NOT change the core meaning or the message. You ENHANCE it visually to guide the reader's eye and emphasize emotional triggers.

### YOUR TOOLKIT (HTML TAGS Supported)
- `<b>...</b>`: Use for key benefits, promises, or strong statements.
- `<i>...</i>`: Use for internal dialogue, thoughts, or subtle emphasis.
- `<u>...</u>`: Use SPARINGLY for the single most important action or warning.
- `Caps`: Use UPPERCASE for individual "Power Words" (e.g., FREE, NEVER, INSTANTLY). Do not use for whole sentences.
- `<br>`: Use for spacing. Short paragraphs are better.
- `<ul><li>...</li></ul>`: Use for lists (if the structure dictates it).

### RULES
1. **Preserve Meaning**: Do not rewrite the copy completely. Just polish and format.
2. **Aggressive Readability**: Break long paragraphs into 1-2 line chunks.
3. **Psychological Bolding**: Bold the *benefit* ("Wake up with **perfect hair**"), not the feature.
4. **Structure Compliance**: 
   - If Structure is `STRUCT_EMOJI_CHECKLIST` or `STRUCT_MEDIA_LEFT_OFFSET`, ensure you return a `<ul>` list.
   - If Structure is `STRUCT_STAT_ATTACK` or `STRUCT_SPOTLIGHT_BOX` or `STRUCT_STEP_BY_STEP` or `STRUCT_MINI_GRID`, you MUST return a `<table>`.
   - For `STRUCT_STAT_ATTACK`: Ensure rows/cols are preserved. Format the text *inside* the cells.
   - For others: Use `<p>` tags separated by `<br>`.
5. **Language**: Keep the Output in **{language}**.
6. **STRICT COMPLIANCE**:
   - **NO** emojis in the body text unless the Structure explicitly requires it.
   - **NO** em-dashes (—) or en-dashes (–). Use commas, periods, or ellipses (...) instead.
   - **NO** hyphens (-) except for grammatical compound words.
   - **NO** hashtags.

### INPUT CONTEXT
- **Brand Voice**: {brand_voice}
- **Structure**: {structure_id}
- **Raw Content**:
"{content}"

### STRICT OUTPUT FORMAT
Return ONLY the formatted HTML string. No markdown block markers (```html). Just the raw HTML string.
"""
        
        try:
            print(f"[Stylist] Polishing content for structure: {structure_id}...")
            response = await self.client.generate_text(system_prompt, model=self.model)
            
            # Clean response (remove generic wrappers if any)
            cleaned = response.strip()
            if cleaned.startswith("```html"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            return cleaned.strip()

        except Exception as e:
            print(f"[Stylist] Error styling content: {e}. Returning raw content.")
            return content
