from typing import Any, Dict
from google.adk.tools.agent_tool import AgentTool
from email_orchestrator.tools.trace_manager import TRACE


class LoggedAgentTool(AgentTool):
    async def run_async(self, args: dict, tool_context: Any = None) -> Any:
        # Log the call
        TRACE.log_tool_call(self.agent.name, args)

        # Map raw_input to request if present (AgentTool expects 'request')
        if "raw_input" in args and "request" not in args:
            args["request"] = args.pop("raw_input")
            
        result = await super().run_async(args=args, tool_context=tool_context)
        
        # Log the result
        TRACE.log_tool_result(self.agent.name, result)
        
        return result

    def declaration(self):
        from google.genai import types
        
        # If the agent has an input_schema, use it. Otherwise default to a generic one.
        # For brief_planner, we know it needs raw_input.
        # Ideally this should be dynamic, but for now we fix the blocker.
        
        return types.FunctionDeclaration(
            name=self.agent.name,
            description=self.agent.description,
            parameters=types.Schema(
                type="object",
                properties={
                    "request": types.Schema(
                        type="string",
                        description="The raw user input describing the campaign details."
                    )
                },
                required=["request"]
            )
        )
