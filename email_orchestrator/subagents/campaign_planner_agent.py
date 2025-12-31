
"""
Campaign Planner Agent - Session-Based Implementation
Uses persistent InMemoryRunner session to maintain context across revisions.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import traceback

from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from email_orchestrator.schemas import BrandBio, CampaignPlan
from email_orchestrator.tools.timing_calculator import calculate_send_schedule, parse_duration_to_start_date
from email_orchestrator.tools.history_manager import HistoryManager
from email_orchestrator.tools.catalog_manager import get_catalog_manager
from email_orchestrator.config import ADK_MODEL

# Initialize managers
history_manager = HistoryManager()
catalog_manager = get_catalog_manager()

def load_campaign_planner_instruction() -> str:
    """Load the campaign planner prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "campaign_planner" / "v1.txt"
    return prompt_path.read_text(encoding="utf-8")

# Create the ADK Agent definition
campaign_planner_adk_agent = Agent(
    model=ADK_MODEL,
    name="campaign_planner",
    description="Strategic multi-email campaign planner with session memory.",
    instruction=load_campaign_planner_instruction(),
    tools=[] # Catalogs provided in context
)

class CampaignPlanningSession:
    """
    Manages a persistent planning session.
    Keeps the conversation history (Request -> Plan -> Feedback -> Revision).
    """
    
    def __init__(self, brand_name: str):
        self.brand_name = brand_name
        self.runner = InMemoryRunner(agent=campaign_planner_adk_agent, app_name="campaign_planner")
        self.session = None # Created on first run
        self.user_id = f"planner_user_{brand_name}"

    async def _ensure_session(self):
        if not self.session:
            self.session = await self.runner.session_service.create_session(
                app_name="campaign_planner",
                user_id=self.user_id
            )

    async def generate_initial_plan(
        self,
        campaign_goal: str,
        total_emails: int,
        duration: str,
        brand_bio: BrandBio,
        start_date: Optional[str] = None,
        excluded_days: List[str] = [],
        promotional_ratio: float = 0.4,
        languages: List[str] = ["FR"],
        notes: Optional[str] = None,
        raw_user_input: Optional[str] = None
    ) -> CampaignPlan:
        """
        Generates the initial plan based on user requirements.
        """
        await self._ensure_session()
        
        print(f"[PlanningSession] Starting new session for {self.brand_name}...")
        
        # 1. Prepare Content
        # Load Catalogs
        catalogs_data = {
            "structures": catalog_manager.get_global_catalog("structures"),
        }
        catalogs_str = json.dumps(catalogs_data, indent=2)
        
        # Calculate Schedule
        # Use explicit start_date if provided, else parse from duration
        if start_date:
            from email_orchestrator.tools.timing_calculator import parse_readable_date
            # Try to parse readable date if it's not ISO
            parsed_start = parse_readable_date(start_date)
            if not parsed_start:
                 # Fallback to duration parser if explicit parse fails (shouldn't happen with robust ISO return from LLM)
                 parsed_start = parse_duration_to_start_date(duration)
        else:
            parsed_start = parse_duration_to_start_date(duration)
            
        send_schedule = calculate_send_schedule(
            parsed_start, 
            total_emails, 
            duration,
            excluded_days=excluded_days
        )
        schedule_str = json.dumps(send_schedule, indent=2)
        
        # Get History
        history_identifier = brand_bio.brand_id if getattr(brand_bio, 'brand_id', None) else self.brand_name
        recent_history = history_manager.get_recent_campaigns(history_identifier, limit=5)
        history_summary = _format_history_for_prompt(recent_history)
        
        # Ratios
        promotional_percentage = int(promotional_ratio * 100)
        educational_percentage = 100 - promotional_percentage
        
        # Target Language
        target_lang = languages[0] if languages else "FR"
        
        # 2. Build Prompt
        prompt = f"""
Please create a campaign plan with the following requirements:

Brand: {self.brand_name}
Goal: {campaign_goal}
Total Emails: {total_emails}
Duration: {duration}
Promotional Ratio: {promotional_percentage}% promotional, {educational_percentage}% educational
Target Language: {target_lang}
IMPORTANT: You MUST write all descriptive fields (Rationale, Angle, Persona, Transformation, CTA Description) in the Target Language. Structure IDs must remain in English as per Catalog.

Send Schedule (pre-calculated):
{schedule_str}

Brand Bio:
{brand_bio.model_dump_json(indent=2)}

=== CATALOG (STRUCTURES ONLY) ===
{catalogs_str}
=================================

Historic Campaigns (AVOID REPEATING THESE CONCEPTS):
{history_summary}

ADDITIONAL CONTEXT/CONSTRAINTS (Adhere strictly if provided):
{notes if notes else "None"}

ORIGINAL USER REQUEST (SOURCE OF TRUTH):
"{raw_user_input if raw_user_input else 'N/A'}"

STRICT DATA ADHERENCE:
1. OFFERS: Check the ORIGINAL USER REQUEST above for specific offers, prices, or discounts. you MUST USE THEM EXACTLY. 
   - DO NOT invent new discounts (e.g., do not say "15% off" if user said " $10 off").
   - DO NOT change product names.
   - COPY details verbatim.
2. If no offers are provided in the Request, use generic placeholders like "[Offer Details Here]". DO NOT HALLUCINATE.

Requirements:
1. Generate CREATIVE, BRAND-SPECIFIC descriptions.
2. Select a valid STRUCTURE ID from the [CATALOG] for every email.
3. Ensure variety.
4. Return ONLY valid JSON matching the CampaignPlan schema.
"""
        # 3. Send to Agent
        response_text = await self._send_message(prompt)
        
        # 4. Parse & Return
        plan = self._parse_to_plan(response_text)
        
        # 5. Inject Context for Propagation
        context_parts = []
        if raw_user_input:
            context_parts.append(f"USER INPUT: {raw_user_input}")
        if notes:
            context_parts.append(f"NOTES: {notes}")
        
        if context_parts:
            plan.campaign_context = "\n\n".join(context_parts)
            
        return plan

    async def process_qa_feedback(
        self,
        original_plan: CampaignPlan,
        verification_feedback: Any
    ) -> CampaignPlan:
        """
        Sends QA feedback to the EXISTING session to request a revision.
        The agent remembers the original constraints from the first message.
        """
        print(f"[PlanningSession] Sending QA feedback to session...")
        
        # Re-load catalogs in case context is lost (though session should keep it, it's safer to provide reference)
        # Actually, for a session, we don't strictly need to dump the whole catalog again if the context window allows.
        # But to be safe, we'll focus on the feedback.
        
        feedback_str = chr(10).join(f"- [Rank {issue.rank}] [{issue.category}] {issue.problem}\n  Rationale: {issue.why_it_matters}\n  Options: {json.dumps(issue.options)}" for issue in verification_feedback.top_improvements)
        
        prompt = f"""
The plan you generated has been reviewed by QA.
VERDICT: {verification_feedback.final_verdict}

STRATEGIC FEEDBACK (FIX THESE ISSUES):
{feedback_str}

REVISION RULES:
1. Fix all issues above.
2. CRITICAL: You must STILL adhere to the ORIGINAL DATES, GOAL, and CONSTRAINTS provided in the first message. Do NOT change the start date or duration unless explicitly asked.
3. Keep the same number of emails ({original_plan.total_emails}).
4. Return the full updated CampaignPlan JSON.
"""
        response_text = await self._send_message(prompt)
        return self._parse_to_plan(response_text)

    async def _send_message(self, text: str) -> str:
        """Helper to send message to runner and collect text response."""
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=text)]
        )
        
        result_text = ""
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=self.session.id,
            new_message=user_content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        result_text += part.text
        return result_text

    def _parse_to_plan(self, text: str) -> CampaignPlan:
        """Helper to clean JSON and parse Pydantic model."""
        cleaned = _clean_json_string(text)
        data = json.loads(cleaned)
        
        # Ensure created_at
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
            
        return CampaignPlan(**data)

# --- Helpers ---

def _clean_json_string(raw_text: str) -> str:
    """Aggressive JSON cleanup"""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()
    if "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        return text[start:end]
    return text

def _format_history_for_prompt(history) -> str:
    """Format history for campaign planner prompt."""
    if not history:
        return "No previous emails found."
    
    summary_lines = []
    for i, entry in enumerate(history):
        persona = "N/A"
        if entry.blueprint and hasattr(entry.blueprint, 'persona_description'):
            persona = entry.blueprint.persona_description
            
        line = (
            f"Email #{i+1} ({entry.timestamp[:10]}): "
            f"Trans='{entry.transformation_description}', "
            f"Struct='{entry.structure_id}', "
            f"Angle='{entry.angle_description}'"
        )
        summary_lines.append(line)
    
    return "\n".join(summary_lines)
