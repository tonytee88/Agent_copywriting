from pathlib import Path
from email_orchestrator.tools.straico_llm import StraicoLLM
from google.adk.agents.llm_agent import Agent  # type: ignore
import os
from dotenv import load_dotenv

# root_agent = Agent(
#     # You can change this to any supported Gemini model in your account.
#     model="gemini-2.5-flash",
#     name="email_orchestrator",
#     description=(
#         "An orchestrator agent that plans and writes e-commerce marketing emails "
#         "(promo, educational, and flows) for Klaviyo x Shopify brands."
#     ),
#     instruction=load_instruction(),
#     # No tools yet – we’ll add tools (Shopify, Klaviyo, etc.) in later versions.
#     tools=[],
# )

def load_instruction():
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator" / "v1.txt"
    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()

load_dotenv()

llm = StraicoLLM(model="openai/gpt-4o-mini")

root_agent = Agent(
    model=llm,
    name="email_orchestrator",
    description="Orchestrator using Straico backend",
    instruction=load_instruction(),
    tools=[],
)