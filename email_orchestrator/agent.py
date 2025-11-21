from pathlib import Path

from google.adk.agents.llm_agent import Agent  # type: ignore


def load_instruction() -> str:
    """Load the system prompt for the orchestrator."""
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator" / "v1.txt"
    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()


root_agent = Agent(
    # You can change this to any supported Gemini model in your account.
    model="gemini-3-pro-preview",
    name="email_orchestrator",
    description=(
        "An orchestrator agent that plans and writes e-commerce marketing emails "
        "(promo, educational, and flows) for Klaviyo x Shopify brands."
    ),
    instruction=load_instruction(),
    # No tools yet – we’ll add tools (Shopify, Klaviyo, etc.) in later versions.
    tools=[],
)
