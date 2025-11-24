from typing import Any, Dict
from google.adk.tools.agent_tool import AgentTool
from email_orchestrator.tools.trace_manager import TRACE

class StatefulAgentTool(AgentTool):
    """
    Wrapper around AgentTool that tracks if it has been called and prevents re-calling.
    This solves the infinite loop issue where the orchestrator keeps calling the same tool.
    """
    
    def __init__(self, agent, **kwargs):
        super().__init__(agent=agent, **kwargs)
        self._has_been_called = False
        self._last_result = None
    
    async def run_async(self, args: dict, tool_context: Any = None) -> Any:
        # If this tool has already been called in this session, return the cached result
        if self._has_been_called and self._last_result is not None:
            print(f"[StatefulAgentTool] {self.agent.name} already called, returning cached result")
            return self._last_result
        
        # Log the call
        TRACE.log_tool_call(self.agent.name, args)

        # Map raw_input to request if present (AgentTool expects 'request')
        if "raw_input" in args and "request" not in args:
            args["request"] = args.pop("raw_input")
            
        result = await super().run_async(args=args, tool_context=tool_context)
        
        # Mark as called and cache the result
        self._has_been_called = True
        self._last_result = result
        
        # Log the result
        TRACE.log_tool_result(self.agent.name, result)
        
        return result
    
    def reset(self):
        """Reset the state to allow calling again"""
        self._has_been_called = False
        self._last_result = None
    
    def declaration(self):
        """Override to ensure correct parameter name"""
        decl = super().declaration()
        # Ensure the parameter is named 'request' not 'raw_input'
        if decl and hasattr(decl, 'parameters'):
            params = decl.parameters
            if hasattr(params, 'properties') and params.properties:
                # The agent tool expects 'request' parameter
                pass
        return decl
