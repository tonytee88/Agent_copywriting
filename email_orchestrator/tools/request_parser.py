import json
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from email_orchestrator.tools.straico_tool import StraicoAPIClient

class CampaignRequest(BaseModel):
    brand_name: str = Field(description="Name of the brand")
    campaign_goal: str = Field(description="Goal or theme of the campaign")
    duration: str = Field(description="Timeframe (e.g., 'October', 'Next Month', 'Jan 1 to Jan 15')")
    total_emails: int = Field(default=3, description="Number of emails")
    promotional_ratio: float = Field(default=0.4, description="Ratio of promotional emails (0.0 to 1.0)")
    notes: Optional[str] = Field(default=None, description="Any additional context, constraints, or specific instructions found in the request")

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
    - campaign_goal: (Required) e.g., "Black Friday", "Welcome Series".
    - duration: (Required) e.g., "November", "Next Month", "Q4". Default to "Next Month" if unclear.
    - total_emails: (Integer) Default to 3 if not specified.
    - promotional_ratio: (Float 0-1) Default to 0.4.
    - notes: (String) Catch-all for ANY other context, constraints, or instructions that don't fit above (e.g. "Skip Dec 25th", "Focus on bundles").
    
    USER INPUT: "{user_input}"
    
    Return ONLY valid JSON matching this structure:
    {{
        "brand_name": "...",
        "campaign_goal": "...",
        "duration": "...",
        "total_emails": 3,
        "promotional_ratio": 0.4,
        "notes": "..."
    }}
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
