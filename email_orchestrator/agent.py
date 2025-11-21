from pathlib import Path
from dotenv import load_dotenv

from email_orchestrator.tools.straico_llm import StraicoLLM
from google.adk.agents.llm_agent import Agent
from email_orchestrator.tools.logged_agent_tool import LoggedAgentTool

from email_orchestrator.subagents.brief_planner_agent import brief_planner_agent
from email_orchestrator.tools.trace_manager import TRACE

#brief_planner_tool = AgentTool(agent=brief_planner_agent)
brief_planner_tool = LoggedAgentTool(agent=brief_planner_agent)

def load_instruction():
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator" / "v1.txt"
    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()

load_dotenv()

llm = StraicoLLM(model="openai/gpt-4o-mini")

TRACE.log_agent_start("email_orchestrator")

root_agent = Agent(
    model=llm,
    name="email_orchestrator",
    description="Orchestrator using Straico backend",
    instruction=load_instruction(),
    tools=[brief_planner_tool],
)