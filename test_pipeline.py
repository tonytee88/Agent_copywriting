import asyncio
import os
from dotenv import load_dotenv

# Ensure env vars are loaded
load_dotenv(dotenv_path="email_orchestrator/.env")

# Import the wrapper that handles the runner correctly
from email_orchestrator.run_wrapper import run_with_trace

async def test_pipeline():
    print("=== STARTING PIPELINE TEST ===")
    
    # Test Input
    prompt = (
        'Create a promotional email for "PopBrush" (https://popbrush.fr). '
        'The offer is 20% off for Boxing Day. '
        'Generate an email with a "Post-Holidays" angle.'
    )
    
    # Run the agent steps via the wrapper
    summary, trace_path, result = await run_with_trace(prompt)
    
    print("\n=== FINAL OUTPUT ===\n")
    print(result)
    
    print("\n=== TRACE SUMMARY ===\n")
    print(summary)
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
