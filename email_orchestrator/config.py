"""
Central configuration for AI models used in the Email Orchestrator.
Change models here to switch between testing (cheaper/faster) and production (higher quality).
"""

# --- ADK Agents (Orchestrator, Campaign Planner) ---
# Supported: "gemini-2.0-flash-exp", "gemini-1.5-pro-preview-0409", "gemini-3-pro-preview"
ADK_MODEL = "gemini-2.0-flash-exp"

# --- Straico Agents (Strategist, Verifier, Drafter, etc.) ---
# Supported: "openai/gpt-4o-2024-11-20", "openai/gpt-5-chat", "openai/gpt-5", "anthropic/claude-sonnet-4", "anthropic/claude-3-5-haiku-20241022"

# 1. Model Definitions (Aliases)
# Creative/Smart models for writing and strategy
MODEL_CLAUDE_SONNET = "anthropic/claude-sonnet-4"
MODEL_GPT4O = "openai/gpt-4o-2024-11-20"
MODEL_GEMINI = "google/gemini-2.5-flash"
MODEL_GPT4 = "openai/gpt-4.1"

# Efficient/Fast models for formatting and simple checks
MODEL_GPT4O_MINI = "openai/gpt-4o-mini" 

# 2. Agent Assignments
MODEL_STRATEGIST = MODEL_GPT4  # Needs deep creativity and structure
MODEL_DRAFTER = MODEL_GPT4     # Needs natural flow and "human" voice
MODEL_VERIFIER = MODEL_GPT4O             # Needs strict logic and rule adherence
MODEL_STYLIST = MODEL_GPT4O         # Needs basic formatting only (Cost saver)
MODEL_RESEARCHER = "perplexity/sonar" # Dedicated research model with live web access

# Fallback / Legacy (for tools not yet updated)
STRAICO_MODEL = MODEL_GPT4O

ENABLE_TRACING = True

# --- Google Drive Settings ---
# Folder to save compiled campaign docs
CAMPAIGN_OUTPUT_FOLDER_ID = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"