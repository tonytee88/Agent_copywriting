import json
import os
import time
import uuid
from typing import Any, Dict

from email_orchestrator.config import ENABLE_TRACING


class TraceManager:
    def __init__(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.events: list[Dict[str, Any]] = []

    # 👇 This is what run_wrapper is calling
    def reset(self) -> None:
        """Reset trace for a new run."""
        if not ENABLE_TRACING:
            return
        self.session_id = str(uuid.uuid4())
        self.events = []

    def log(self, type: str, **kwargs: Any) -> None:
        if not ENABLE_TRACING:
            return

        self.events.append(
            {
                "time": time.time(),
                "type": type,
                **kwargs,
            }
        )

    def log_agent_start(self, agent: str) -> None:
        self.log("agent_start", agent=agent)

    def log_agent_end(self, agent: str) -> None:
        self.log("agent_end", agent=agent)

    def log_tool_call(self, tool: str, args: Any) -> None:
        self.log("tool_call", tool=tool, args=self._safe_repr(args))

    def log_tool_result(self, tool: str, result: Any) -> None:
        self.log("tool_result", tool=tool, result=self._safe_repr(result))

    def log_llm_request(self, agent: str, messages: Any) -> None:
        self.log("llm_request", agent=agent, messages=self._safe_repr(messages))

    def log_llm_response(self, agent: str, content: str) -> None:
        self.log("llm_response", agent=agent, content=content)

    # 👇 Optional: log raw events from InMemoryRunner
    def log_event(self, event: Any) -> None:
        """
        Store a minimal version of the ADK event.
        We don't serialize everything – just enough to debug the path.
        """
        if not ENABLE_TRACING:
            return

        event_type = getattr(event, "event_type", None)
        
        # Infer type if missing
        # Infer type and content
        if not event_type:
            # Check if it's a model response (has content)
            if getattr(event, "content", None):
                event_type = "model_turn"
            # Check if it's a tool request (has function_call) - though usually inside content
            elif hasattr(event, "tool_calls"):
                event_type = "tool_call_request"
            else:
                event_type = "unknown_event"

        data: Dict[str, Any] = {
            "event_type": event_type,
        }

        # if there's content text, include a short preview
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            texts = []
            for p in content.parts:
                # 1. Text content
                txt = getattr(p, "text", "")
                if txt:
                    texts.append(txt)
                
                # 2. Function calls (Tool Requests)
                if getattr(p, "function_call", None):
                    fc = p.function_call
                    # Log this as a special TOOL_CALL event type for better visibility
                    data["event_type"] = "TOOL_CALL"
                    data["tool_name"] = fc.name
                    # Truncate args if too long
                    args_str = str(fc.args)
                    if len(args_str) > 100:
                        args_str = args_str[:100] + "..."
                    texts.append(f"Calling tool: {fc.name}({args_str})")
                
                # 3. Function responses (Tool Results)
                if getattr(p, "function_response", None):
                    fr = p.function_response
                    # Log this as a special TOOL_RESULT event type
                    data["event_type"] = "TOOL_RESULT"
                    data["tool_name"] = fr.name
                    # Truncate result if too long
                    resp_str = str(fr.response)
                    if len(resp_str) > 150:
                        resp_str = resp_str[:150] + "..."
                    texts.append(f"Tool returned: {fr.name} -> {resp_str}")
                    
            if texts:
                data["content_preview"] = " | ".join(texts)[:300]

        self.log("runner_event", **data)

    def export(self, directory: str = "traces") -> str | None:
        if not ENABLE_TRACING:
            return None

        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, f"trace_{self.session_id}.json")

        with open(filename, "w") as f:
            json.dump(self.events, f, indent=2)

        return filename

    def pretty_print(self) -> str:
        if not ENABLE_TRACING:
            return ""

        lines: list[str] = []
        for e in self.events:
            t = time.strftime("%H:%M:%S", time.localtime(e["time"]))
            etype = e["type"]

            if etype == "agent_start":
                lines.append(f"{t} [START] Agent {e['agent']}")
            elif etype == "agent_end":
                lines.append(f"{t} [END] Agent {e['agent']}")
            elif etype == "tool_call":
                lines.append(f"{t} → TOOL CALL: {e['tool']}")
            elif etype == "tool_result":
                lines.append(f"{t} ← TOOL RESULT: {e['tool']}")
            elif etype == "llm_request":
                lines.append(f"{t} → LLM REQUEST ({e['agent']})")
            elif etype == "llm_response":
                lines.append(f"{t} ← LLM RESPONSE ({e['agent']})")
            elif etype == "runner_event":
                evt_type = e.get('event_type')
                content = e.get('content_preview', '')
                
                if evt_type == "TOOL_CALL":
                    lines.append(f"{t} 🛠️  TOOL CALL: {e.get('tool_name')} → {content}")
                elif evt_type == "TOOL_RESULT":
                    lines.append(f"{t} ✅ TOOL RESULT: {e.get('tool_name')} → {content}")
                else:
                    lines.append(
                        f"{t} [EVENT] {evt_type} "
                        f"{('→ ' + content) if content else ''}"
                    )

        return "\n".join(lines)

    @staticmethod
    def _safe_repr(obj: Any) -> Any:
        """Best-effort serialization: avoid blowing up on non-JSON stuff."""
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            return repr(obj)


# Global trace instance
TRACE = TraceManager()
