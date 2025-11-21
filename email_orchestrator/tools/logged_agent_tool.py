from google.adk.tools.agent_tool import AgentTool
from email_orchestrator.tools.trace_manager import TRACE


class LoggedAgentTool(AgentTool):
    async def run_tool_async(self, *args, **kwargs):
        TRACE.log_tool_call(self.agent.name, args)

        result = await super().run_tool_async(*args, **kwargs)

        TRACE.log_tool_result(self.agent.name, result)
        return result
