# email_orchestrator/run_wrapper.py

from typing import Tuple

from google.adk.runners import InMemoryRunner  # type: ignore
from google.genai import types as genai_types  # type: ignore

from email_orchestrator.agent import root_agent
from email_orchestrator.tools.trace_manager import TRACE

APP_NAME = "email_orchestrator_app"
USER_ID = "local_user"

# Single runner instance for the app
runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)


async def run_with_trace(user_message: str) -> Tuple[str, str | None, str]:
    """
    Run the root orchestrator agent (with tools) via InMemoryRunner + tracing.

    Returns:
      summary: human-readable trace summary
      trace_path: path to the saved trace JSON (or None if tracing disabled)
      final_text: assistant's final text response
    """
    # Reset tracing for this turn
    TRACE.reset()
    TRACE.log_agent_start("email_orchestrator")

    # Create a new session for this run.
    # (Later we can re-use session.id for multi-turn convos.)
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    # Build the user message as a Content object
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    final_text = ""

    # Run the orchestrator via the Runner – this will internally
    # handle tool calls (brief_planner) thanks to StraicoLLM supporting tools.
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=user_content,
    ):
        # Optional: log raw events into the trace
        TRACE.log_event(event)

        # Collect assistant text from events
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text += part.text

    TRACE.log_agent_end("email_orchestrator")

    trace_path = TRACE.export()
    summary = TRACE.pretty_print()

    return summary, trace_path, final_text
