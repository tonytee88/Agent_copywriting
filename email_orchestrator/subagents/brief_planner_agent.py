from pathlib import Path
from email_orchestrator.tools.straico_llm import StraicoLLM
from google.adk.agents.llm_agent import Agent

def load_instruction():
    prompt_path = Path(__file__).parent.parent / "prompts" / "brief_planner" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")


# You can pick any Straico-supported model here
llm = StraicoLLM(model="openai/gpt-4o-mini")

brief_planner_agent = Agent(
    model=llm,
    name="brief_planner",
    description="Create a structured [BRIEF] block for an e-commerce email.",
    instruction=load_instruction(),
    tools=[],
    
)
