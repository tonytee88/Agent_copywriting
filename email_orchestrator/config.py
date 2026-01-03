"""
Central configuration for AI models used in the Email Orchestrator.
Change models here to switch between testing (cheaper/faster) and production (higher quality).
"""

# --- ADK Agents (Orchestrator, Campaign Planner) ---
# Supported: "gemini-2.0-flash-exp", "gemini-1.5-pro-preview-0409", "gemini-3-pro-preview"
ADK_MODEL = "gemini-2.0-flash-exp"

# --- Straico Agents (Strategist, Verifier, Drafter, etc.) ---
# --- Straico Agents (Strategist, Verifier, Drafter, etc.) ---
# Supported: "openai/gpt-4o-2024-11-20", "openai/gpt-5-chat", "openai/gpt-3.5-turbo", "anthropic/claude-3-5-sonnet-20240620"

# 1. Model Definitions (Aliases)
# Creative/Smart models for writing and strategy
MODEL_CLAUDE_SONNET = "anthropic/claude-3-5-sonnet-20240620" 
MODEL_GPT4O = "openai/gpt-4o-2024-11-20"

# Efficient/Fast models for formatting and simple checks
MODEL_GPT4O_MINI = "openai/gpt-4o-mini" 
MODEL_GPT35 = "openai/gpt-3.5-turbo"

# 2. Agent Assignments
MODEL_STRATEGIST = MODEL_CLAUDE_SONNET   # Needs deep creativity and structure
MODEL_DRAFTER = MODEL_CLAUDE_SONNET      # Needs natural flow and "human" voice
MODEL_VERIFIER = MODEL_GPT4O             # Needs strict logic and rule adherence
MODEL_STYLIST = MODEL_GPT4O_MINI         # Needs basic formatting only (Cost saver)

# Fallback / Legacy (for tools not yet updated)
STRAICO_MODEL = MODEL_GPT4O

ENABLE_TRACING = True

# --- Google Drive Settings ---
# Folder to save compiled campaign docs
CAMPAIGN_OUTPUT_FOLDER_ID = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"