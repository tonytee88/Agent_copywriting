from pathlib import Path
from google.adk.agents.llm_agent import Agent  # type: ignore

from email_orchestrator.config import STRAICO_MODEL

def load_instruction() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "persona" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")

def _get_llm():
    """Lazy load LLM to avoid import-time API key errors"""
    from email_orchestrator.tools.straico_llm import StraicoLLM
    return StraicoLLM(model=STRAICO_MODEL)

persona_agent = Agent(
    model=_get_llm(),
    name="persona_selector",
    description=(
        "Selects the best persona and transformation angle based on the campaign brief. "
        "\n\nWHEN TO USE THIS TOOL:"
        "\n- AFTER you have received a [BRIEF] from brief_planner"
        "\n- When you DON'T have a [CHOSEN PERSONA] and [CHOSEN TRANSFORMATION] yet"
        "\n- You need to determine the target persona for the email"
        "\n\nDO NOT USE THIS TOOL:"
        "\n- BEFORE calling brief_planner (you need a brief first)"
        "\n- If you ALREADY have persona and transformation selected"
        "\n- After this tool has already returned a result"
        "\n\nINPUT: The [BRIEF] content"
        "\nOUTPUT: Returns [CHOSEN PERSONA] and [CHOSEN TRANSFORMATION]"
    ),
    instruction=load_instruction(),
)
