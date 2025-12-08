"""
Simple tool wrappers for Straico API calls.
These are used by the Gemini orchestrator as regular function tools.
"""

import os
import aiohttp
import json
from pathlib import Path

# Environment variables are loaded by the main orchestrator; no need to load .env here


class StraicoAPIClient:
    """Simple client for making Straico API requests"""
    
    def __init__(self):
        self.api_key = os.getenv("STRAICO_API_KEY")
        if not self.api_key:
            raise ValueError("STRAICO_API_KEY not set in environment")
        self.base_url = "https://api.straico.com/v2"
    
    async def generate_text(self, prompt: str, model: str = "openai/gpt-4o-2024-11-20") -> str:
        """
        Make a simple text generation request to Straico API.
        No tool calling, just text in/text out.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        body = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
        }
        
        timeout = aiohttp.ClientTimeout(total=120)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(f"Straico API error {resp.status}: {error_text}")
                    
                    resp_json = await resp.json()
                    
                    # Extract text from response
                    choices = resp_json.get("choices", [])
                    if not choices:
                        return ""
                    
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    
                    return content
                    
        except Exception as e:
            print(f"[StraicoAPIClient] Error: {e}")
            return f"Error calling Straico API: {str(e)}"


# Global client instance
_client = None

def get_client() -> StraicoAPIClient:
    """Get or create the Straico API client"""
    global _client
    if _client is None:
        _client = StraicoAPIClient()
    return _client


# ============================================================================
# TOOL FUNCTIONS - These are registered with the Gemini orchestrator
# ============================================================================

async def brief_planner(campaign_details: str) -> str:
    """
    Creates a structured campaign brief from user's campaign details.
    
    WHEN TO USE:
    - At the START of a new email campaign
    - When you DON'T have a [BRIEF] yet
    - User provides campaign details (promo, products, audience, etc.)
    
    DO NOT USE:
    - If you ALREADY have a [BRIEF] in the conversation
    - After this tool has already returned a brief
    
    Args:
        campaign_details: The user's campaign description
        
    Returns:
        A structured [BRIEF] block with campaign details
    """
    # Load the brief planner prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "brief_planner" / "v1.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    # Build the full prompt
    full_prompt = f"{prompt_template}\n\nUser's campaign details:\n{campaign_details}"
    
    # Call Straico API
    client = get_client()
    result = await client.generate_text(full_prompt)
    
    print(f"[brief_planner] Generated brief ({len(result)} chars)")
    return result


async def persona_selector(brief: str) -> str:
    """
    Selects the best persona and transformation angle based on the campaign brief.
    
    WHEN TO USE:
    - AFTER you have received a [BRIEF] from brief_planner
    - When you DON'T have a [CHOSEN PERSONA] and [CHOSEN TRANSFORMATION] yet
    
    DO NOT USE:
    - BEFORE calling brief_planner (you need a brief first)
    - If you ALREADY have persona and transformation selected
    
    Args:
        brief: The campaign brief (output from brief_planner)
        
    Returns:
        [CHOSEN PERSONA] and [CHOSEN TRANSFORMATION]
    """
    # Load the persona selector prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "persona" / "v1.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    # Build the full prompt
    full_prompt = f"{prompt_template}\n\nCampaign Brief:\n{brief}"
    
    # Call Straico API
    client = get_client()
    result = await client.generate_text(full_prompt)
    
    print(f"[persona_selector] Selected persona ({len(result)} chars)")
    return result


async def email_drafter(brief: str, persona: str) -> str:
    """
    Writes the final email draft based on the brief and persona.
    
    WHEN TO USE:
    - AFTER you have BOTH a [BRIEF] and a [CHOSEN PERSONA].
    - This is the final step to generate the actual email content.
    
    DO NOT USE:
    - If you are missing the brief or the persona.
    
    Args:
        brief: The full campaign brief.
        persona: The selected persona and transformation angle.
        
    Returns:
        The complete email draft.
    """
    # Load the drafter prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "drafter" / "v1.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    # Build the full prompt
    full_prompt = f"{prompt_template}\n\n=== INPUTS ===\n\n[BRIEF]:\n{brief}\n\n[PERSONA]:\n{persona}"
    
    # Call Straico API
    client = get_client()
    result = await client.generate_text(full_prompt)
    
    print(f"[email_drafter] Generated draft ({len(result)} chars)")
    return result
