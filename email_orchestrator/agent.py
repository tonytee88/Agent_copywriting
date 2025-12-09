# email_orchestrator/agent.py

from pathlib import Path
import os

from dotenv import load_dotenv

# Load environment variables from the .env file located in this package
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from google.adk.agents.llm_agent import Agent  # type: ignore
from google import genai

# Import our Straico tool functions
# Import our Campaign tools
from email_orchestrator.tools.campaign_tools import analyze_brand, generate_email_campaign


def load_instruction() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator" / "v6.txt"
    return prompt_path.read_text(encoding="utf-8")


# Use Gemini for orchestrator (supports reliable tool calling!)
# ADK has built-in support for Gemini models via google-genai
# Just pass the model name and set GOOGLE_API_KEY env var

# Create orchestrator with Gemini model
root_agent = Agent(
    model="gemini-2.0-flash",  # Valid model from list
    name="email_orchestrator",
    description=(
        "An orchestrator agent that plans and writes e-commerce marketing emails "
        "(promo, educational, and flows) for Klaviyo x Shopify brands."
    ),
    instruction=load_instruction(),
    tools=[
        analyze_brand,
        generate_email_campaign,
    ],
)
