# email_orchestrator/run_wrapper.py

import asyncio
from typing import Tuple

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from email_orchestrator.agent import root_agent
from email_orchestrator.tools.trace_manager import TRACE

APP_NAME = "email_orchestrator_app"
USER_ID = "local_user"  # you can change this later if you want per-user IDs


# Create the runner once, re-used across calls
runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)


async def run_with_trace(user_message: str) -> Tuple[str, str | None, str]:
    TRACE.reset()
    TRACE.log_agent_start("email_orchestrator")

    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    final_text = ""

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=user_content,
    ):
        TRACE.log_event(event)

        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text += part.text

    TRACE.log_agent_end("email_orchestrator")
    trace_path = TRACE.export()
    summary = TRACE.pretty_print()

    return summary, trace_path, final_text
