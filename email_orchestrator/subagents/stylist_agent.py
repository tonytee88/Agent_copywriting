import json
import os
from typing import Dict, Any, Optional

from email_orchestrator.tools.straico_tool import StraicoAPIClient
from email_orchestrator.tools.straico_tool import StraicoAPIClient
from email_orchestrator.config import MODEL_STYLIST

class StylistAgent:
    """
    Subagent responsible for polishing and formatting the 'Descriptive Block' 
    of an email to maximize readability and conversion using tactical formatting.
    """

    def __init__(self, model: str = MODEL_STYLIST):
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
        
        # TEMPLATE DEFINITIONS (Agile & Strict)
        templates = {
            "STRUCT_NARRATIVE_PARAGRAPH": "<h3>[Headline].</h3><br><p>[Body Text 2-4 lines max]</p><br><p><i>[Optional subtle closing thought]</i></p>",
            
            "STRUCT_EMOJI_CHECKLIST": "<h3>[Headline]</h3><br><ul><li><b>[Emoji] [Benefit 1]:</b> [Short explanation]</li><li><b>[Emoji] [Benefit 2]:</b> [Short explanation]</li><li><b>[Emoji] [Benefit 3]:</b> [Short explanation]</li></ul>",
            
            "STRUCT_5050_SPLIT": "<table width='100%'><tr><td width='50%' valign='middle'><img src='[ImagePlaceholder]' alt='[Alt]' width='100%'></td><td width='50%' valign='middle' style='padding-left: 15px;'><p>[Body Text]</p></td></tr></table>",
            
            "STRUCT_MEDIA_LEFT_OFFSET": "<table width='100%'><tr><td width='30%' valign='top' style='padding-right: 10px;'><img src='[Icon/Image]' width='100%'></td><td width='70%' valign='top'><p>[Body Text]</p></td></tr></table>",
            
            "STRUCT_SPOTLIGHT_BOX": "<table width='100%' style='background-color: #f4f4f4; border-radius: 8px;'><tr><td style='padding: 20px; text-align: center;'><h3>[Urgent Headline]</h3><p>[Short persuasive text]</p><br><b>[Key Takeaway/Code]</b></td></tr></table>",
            
            "STRUCT_STAT_ATTACK": "<table width='100%' style='text-align: center;'><tr><td width='33%'><h1>[Stat 1]</h1><br><p>[Label 1]</p></td><td width='33%'><h1>[Stat 2]</h1><br><p>[Label 2]</p></td><td width='33%'><h1>[Stat 3]</h1><br><p>[Label 3]</p></td></tr><tr><td width='33%' valign='top'><p>[Short explanation (1-2 lines max)]</p></td><td width='33%' valign='top'><p>[Short explanation (1-2 lines max)]</p></td><td width='33%' valign='top'><p>[Short explanation (1-2 lines max)]</p></td></tr></table>",
            
            "STRUCT_STEP_BY_STEP": "<p><b>Step 1:</b> [Action]</p><br><br><p><b>Step 2:</b> [Action]</p><br><br><p><b>Step 3:</b> [Action]</p>",
            
            "STRUCT_MINI_GRID": "<table width='100%'><tr><td width='33%'><img src='[Item1]' width='100%'><p align='center'>[Label 1]</p></td><td width='33%'><img src='[Item2]' width='100%'><p align='center'>[Label 2]</p></td><td width='33%'><img src='[Item3]' width='100%'><p align='center'>[Label 3]</p></td></tr></table>",
            
            "STRUCT_SOCIAL_PROOF_QUOTE": "<div style='text-align: center; font-style: italic; padding: 15px;'><p>&quot;[Quote Text]&quot;</p><br><p><b>— [Customer Name]</b>, Verified Buyer</p></div>",
            
            "STRUCT_GIF_PREVIEW": "<table width='100%' style='border: 1px dashed #999; background-color: #f9f9f9;'><tr><td style='padding: 20px; text-align: center;'><b>[[GIF IDEA: [Describe visual... 1-2 lines]]]</b></td></tr></table><br><p>[SUMMARIZE content into 2-3 punchy lines max. Do NOT include full body text. Support the GIF and push to CTA.]</p>"
        }
        
        target_template = templates.get(structure_id, "<h3>[Headline]</h3><p>[Formatted Body Text]</p>")

        system_prompt = f"""
You are an expert **Copy Editor and Direct Response Stylist**.
Your job is to take raw email body text and transform it into a **visually engaging, highly readable masterpiece** using "Tactical Formatting".

### TASK:
Format the "Raw Content" into the "Target HTML Template".

### TARGET HTML TEMPLATE (STRICTLY FOLLOW THIS STRUCTURE):
{target_template}

### RULES
1. **Fill the slots**: Replace placeholders like `[Headline]`, `[Body Text]`, etc. with the content from "Raw Content".
2. **Preserve Meaning**: Do not rewrite the core message, just fit it into the container.
3. **Psychological Bolding**: Use `<b>` for key benefits inside paragraphs.
4. **Language**: Keep the Output in **{language}**.
5. **Clean HTML**: Return ONLY valid HTML tags. No `<html>` or `<body>` wrappers.
6. **Casing (CRITICAL)**:
   - **French (FR)**: Headlines inside `<h3>` MUST use **Sentence case** (Only first letter capitalized). NEVER use Title Case (e.g., "Améliorez vos compétences" NOT "Améliorez Vos Compétences").
   - **English (EN)**: Use standard casing.
7. **Rhythm & Flow (CRITICAL)**:
   - **No Walls of Text**: Aggressively use `<br><br>` (Double Line Break) to create clear paragraphs and white space. Denser text blocks (>3 lines) are forbidden.
   - **Suspense**: Use single `<br>` to isolate punchlines or key thoughts.
   - **Variety**: Mix short, punchy sentences with longer, flowing ones.
   - **Pacing**: Use ellipses (...) or em-dashes (—) *only if appropriate for the voice* to create pauses.

### INPUT CONTEXT
- **Brand Voice**: {brand_voice}
- **Raw Content**:
"{content}"

### STRICT OUTPUT FORMAT
Return ONLY the formatted HTML string.
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
