from pathlib import Path
from google.adk.agents.llm_agent import Agent  # type: ignore

from email_orchestrator.config import STRAICO_MODEL

def load_instruction() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "brief_planner" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")

def _get_llm():
    """Lazy load LLM to avoid import-time API key errors"""
    from email_orchestrator.tools.straico_llm import StraicoLLM
    return StraicoLLM(model=STRAICO_MODEL)

brief_planner_agent = Agent(
    model=_get_llm(),
    name="brief_planner",
    description=(
        "Creates the initial campaign brief from user's campaign details. "
        "\n\nWHEN TO USE THIS TOOL:"
        "\n- At the START of a new email campaign"
        "\n- When you DON'T have a [BRIEF] yet"
        "\n- User provides campaign details (promo, products, audience, etc.)"
        "\n\nDO NOT USE THIS TOOL:"
        "\n- If you ALREADY have a [BRIEF] in the conversation"
        "\n- After this tool has already returned a brief"
        "\n- For updating an existing brief"
        "\n\nOUTPUT: Returns a structured [BRIEF] block with campaign details."
    ),
    instruction=load_instruction(),
    tools=[],
    
)
 