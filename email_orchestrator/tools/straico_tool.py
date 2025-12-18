"""
Simple tool wrappers for Straico API calls.
These are used by the Gemini orchestrator as regular function tools.
"""

import os
import aiohttp
import asyncio
import random
import json
from pathlib import Path

# Environment variables are loaded by the main orchestrator; no need to load .env here

from email_orchestrator.config import STRAICO_MODEL


class StraicoAPIClient:
    """Simple client for making Straico API requests"""
    
    def __init__(self):
        self.api_key = os.getenv("STRAICO_API_KEY")
        if not self.api_key:
            raise ValueError("STRAICO_API_KEY not set in environment")
        self.base_url = "https://api.straico.com/v2"
    
    async def generate_text(self, prompt: str, model: str = STRAICO_MODEL) -> str:
        """
        Make a simple text generation request to Straico API.
        Includes retry logic for server errors (502, 503, 504).
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
        max_retries = 5
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, headers=headers, json=body) as resp:
                        
                        # 1. Handle Success
                        if resp.status == 200:
                            resp_json = await resp.json()
                            
                            # Extract text
                            choices = resp_json.get("choices", [])
                            if not choices:
                                return ""
                            
                            message = choices[0].get("message", {})
                            content = message.get("content", "")
                            
                            # Track usage
                            usage = resp_json.get("usage", {})
                            prompt_tokens = usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("completion_tokens", 0)
                            
                            if prompt_tokens > 0:
                                from email_orchestrator.tools.token_tracker import get_token_tracker
                                get_token_tracker().log_usage("StraicoAPI", prompt_tokens, completion_tokens)
                            
                            return content

                        # 2. Handle Retryable Server Errors
                        elif resp.status in [502, 503, 504]:
                            error_text = await resp.text()
                            print(f"[StraicoAPI] Server Error {resp.status} on attempt {attempt+1}/{max_retries}. Retrying...")
                            
                            if attempt < max_retries - 1:
                                # Exponential backoff + jitter
                                delay = (base_delay * (2 ** attempt)) + (random.random() * 1.0)
                                print(f"[StraicoAPI] Waiting {delay:.2f}s...")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                raise RuntimeError(f"Straico API failed after {max_retries} retries. Last code: {resp.status}. Error: {error_text}")

                        # 3. Handle Non-Retryable Client Errors (400, 401, etc.)
                        else:
                            error_text = await resp.text()
                            raise RuntimeError(f"Straico API Client Error {resp.status}: {error_text}")
                            
            except aiohttp.ClientError as e:
                # Network level errors (connection refused, etc.) are also retryable
                print(f"[StraicoAPI] Network Error on attempt {attempt+1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    delay = (base_delay * (2 ** attempt)) + (random.random() * 1.0)
                    print(f"[StraicoAPI] Waiting {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"[StraicoAPIClient] Final Network Error: {e}")
                    raise e
                    
            except Exception as e:
                # Other unexpected errors
                print(f"[StraicoAPIClient] Unexpected Error: {e}")
                raise e
        
        return ""


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
