from pathlib import Path
from email_orchestrator.tools.straico_llm import StraicoLLM
from google.adk.agents.llm_agent import Agent  # type: ignore
import os
from dotenv import load_dotenv
from google.adk.tools.agent_tool import AgentTool
from .subagents.brief_planner_agent import brief_planner_agent

brief_planner_tool = AgentTool(agent=brief_planner_agent)

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
    tools=[brief_planner_tool],
)