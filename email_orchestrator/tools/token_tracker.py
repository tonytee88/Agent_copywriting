from typing import Dict, Any, List
from collections import defaultdict

class TokenTracker:
    """
    Singleton to track token usage across the application execution.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TokenTracker, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
            
        self.reset()
        self.initialized = True
        
    def reset(self):
        """Reset all counters."""
        self.usage_log: List[Dict[str, Any]] = []
        self.totals = defaultdict(int) # total_prompt, total_completion, total_all
        self.by_agent = defaultdict(lambda: defaultdict(int)) # agent -> {prompt, completion, total}
        
    def log_usage(self, agent_name: str, prompt_tokens: int, completion_tokens: int):
        """Log a single API call's usage."""
        total = prompt_tokens + completion_tokens
        
        # Record event
        self.usage_log.append({
            "agent": agent_name,
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total
        })
        
        # Update totals
        self.totals["prompt"] += prompt_tokens
        self.totals["completion"] += completion_tokens
        self.totals["all"] += total
        
        # Update agent stats
        self.by_agent[agent_name]["prompt"] += prompt_tokens
        self.by_agent[agent_name]["completion"] += completion_tokens
        self.by_agent[agent_name]["total"] += total

    def get_summary(self) -> str:
        """Generate a formatted summary string."""
        if self.totals["all"] == 0:
            return "No token usage recorded."
            
        lines = ["\n=== TOKEN USAGE REPORT ==="]
        lines.append(f"TOTAL: {self.totals['all']:,} tokens (Prompt: {self.totals['prompt']:,} / Completion: {self.totals['completion']:,})")
        lines.append("-" * 30)
        
        # Sort agents by total usage descending
        sorted_agents = sorted(self.by_agent.items(), key=lambda x: x[1]["total"], reverse=True)
        
        for agent, stats in sorted_agents:
            lines.append(f"{agent:<20}: {stats['total']:,} ({stats['prompt']:,} in / {stats['completion']:,} out)")
            
        lines.append("==========================\n")
        return "\n".join(lines)

# Global instance getter
def get_token_tracker() -> TokenTracker:
    return TokenTracker()
