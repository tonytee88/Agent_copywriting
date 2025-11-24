# email_orchestrator/agent.py

from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent  # type: ignore

from email_orchestrator.tools.straico_llm import StraicoLLM
from email_orchestrator.tools.logged_agent_tool import LoggedAgentTool
from email_orchestrator.subagents.brief_planner_agent import brief_planner_agent


def load_instruction() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")


load_dotenv()

# Main LLM for the orchestrator (Straico backend)
llm = StraicoLLM(model="openai/gpt-4o-2024-08-06")

# Brief Planner tool – wraps the brief_planner_agent
brief_planner_tool = LoggedAgentTool(agent=brief_planner_agent)

root_agent = Agent(
    model=llm,
    name="email_orchestrator",
    description=(
        "An orchestrator agent that plans and writes e-commerce marketing emails "
        "(promo, educational, and flows) for Klaviyo x Shopify brands."
    ),
    instruction=load_instruction(),
    tools=[
        brief_planner_tool,
    ],
)
