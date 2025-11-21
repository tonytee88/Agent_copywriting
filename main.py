# main.py at project root

import asyncio
from email_orchestrator.run_wrapper import run_with_trace

if __name__ == "__main__":
    print("Email Orchestrator CLI (with tracing). Type an empty line to quit.\n")
    while True:
        user_input = input("> ").strip()
        if not user_input:
            break

        summary, trace_path, output = asyncio.run(run_with_trace(user_input))

        print("\n=== ASSISTANT OUTPUT ===\n")
        print(output)

        print("\n=== TRACE SUMMARY ===\n")
        print(summary)

        print(f"\n[trace saved to: {trace_path}]\n")
