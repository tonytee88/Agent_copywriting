"""
Central configuration for AI models used in the Email Orchestrator.
Change models here to switch between testing (cheaper/faster) and production (higher quality).
"""

# --- ADK Agents (Orchestrator, Campaign Planner) ---
# Supported: "gemini-2.0-flash-exp", "gemini-1.5-pro-preview-0409", "gemini-3-pro-preview"
ADK_MODEL = "gemini-2.0-flash-exp"

# --- Straico Agents (Strategist, Verifier, Drafter, etc.) ---
# Supported: "openai/gpt-4o-2024-11-20", "openai/gpt-5-chat", "openai/gpt-3.5-turbo", "anthropic/claude-3-5-sonnet-20240620"
STRAICO_MODEL = "openai/gpt-4o-mini"

ENABLE_TRACING = True