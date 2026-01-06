import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from email_orchestrator.tools.straico_tool import StraicoAPIClient

class CampaignRequest(BaseModel):
    brand_name: str = Field(description="Name of the brand")
    campaign_goal: str = Field(description="Goal or theme of the campaign")
    duration: str = Field(description="Timeframe (e.g., 'October', 'Next Month', 'Jan 1 to Jan 15')")
    start_date: Optional[str] = Field(default=None, description="Specific start date if mentioned (YYYY-MM-DD or readable string)")
    excluded_days: List[str] = Field(default=[], description="List of days to exclude (e.g. ['Sunday', 'Saturday'])")
    total_emails: int = Field(default=3, description="Number of emails")
    promotional_ratio: float = Field(default=0.4, description="Ratio of promotional emails (0.0 to 1.0)")
    languages: List[str] = Field(default=["FR"], description="List of target languages (e.g. ['FR', 'EN'])")
    notes: Optional[str] = Field(default=None, description="Any additional context, constraints, or instruction")
    website_url: Optional[str] = Field(default=None, description="Website URL if provided (implied or explicit)")

async def parse_campaign_request(user_input: str) -> CampaignRequest:
    """
    Uses LLM to extract campaign parameters from natural language input.
    """
    client = StraicoAPIClient()
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    You are a request parser for an email campaign orchestrator.
    Current Date: {current_date}
    
    Extract the following fields from the User Input:
    - brand_name: (Required) Guess if implied or explicit.
    - website_url: (Optional) Extract if User provides a URL (e.g. "https://brand.com" or "brand.com").
    - campaign_goal: (Required) e.g., "Black Friday", "Welcome Series".
    - duration: (Required) e.g., "November", "Next Month", "Q4". Default to "Next Month" if unclear.
    - start_date: (Optional) If user specifies a start date (e.g. "starting Jan 7th"), extract it here.
    - excluded_days: (Optional List) If user says "no Sundays" or "exclude weekends", return ["Sunday"] or ["Saturday", "Sunday"].
    - total_emails: (Integer) Look for explicit numbers (e.g. "1 email", "3 emails", "5-email sequence"). Default to 3 ONLY if strictly not specified.
    - promotional_ratio: (Float 0-1) Default to 0.4.
    - notes: (String) Catch-all for ANY other context, constraints, or instruction.
    
    USER INPUT: "{user_input}"
    
    Return ONLY valid JSON matching this structure:
    {{
        "brand_name": "...",
        "website_url": "...",
        "campaign_goal": "...",
        "duration": "...",
        "start_date": "...",
        "excluded_days": ["..."],
        "total_emails": 3,
        "promotional_ratio": 0.4,
        "languages": ["FR"],
        "notes": "..."
    }}

    Language Rules:
    - Default to ["FR"] if not specified.
    - If user says "in English" or "en Anglais", return ["EN"].
    - If user says "in French" or "en FR" or "en Français", return ["FR"].
    - If user says "French and English" or "FR + EN", return ["FR", "EN"].
    - If user says "English and French", return ["FR", "EN"] order is always FR then EN unless specifically mapped otherwise.
    """
    
    try:
        response = await client.generate_text(prompt, model="openai/gpt-4o-mini")
        
        # Cleanup JSON
        cleaned = response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
            
        data = json.loads(cleaned)
        return CampaignRequest(**data)
        
    except Exception as e:
        print(f"[RequestParser] Error: {e}")
        # Fallback for critical failure - though prompt is robust
        return CampaignRequest(
            brand_name="Unknown Brand",
            campaign_goal="General Campaign",
            duration="Next Month",
            notes=f"Failed to parse input. Original text: {user_input}"
        )
