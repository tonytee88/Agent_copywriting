"""
Helper tools for the Campaign Planner ADK Agent.
These tools provide contextual suggestions for strategic content selection.
"""

from typing import List, Dict, Any
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager

from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.config import STRAICO_MODEL
from pathlib import Path
from email_orchestrator.schemas import CampaignPlan, BrandBio
import asyncio

# Initialize tools
knowledge_reader = KnowledgeReader()
history_manager = HistoryManager()

async def brainstorm_transformations(
    brand_bio: BrandBio,
    campaign_goal: str,
    product: str,
    purpose: str,
    structure: str
) -> List[Dict]:
    """
    Agent A: Generates 3 transformation options.
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "campaign_planner" / "transformation_brainstormer.txt"
    template = prompt_path.read_text(encoding="utf-8")
    
    # Get catalog sample
    catalog_content = knowledge_reader.get_document_content("Transformations v2.pdf")
    catalog_sample = catalog_content[:1500] # Truncate for token efficiency

    full_prompt = template.format(
        brand_bio=brand_bio.model_dump_json(),
        campaign_goal=campaign_goal,
        product=product,
        purpose=purpose,
        structure=structure,
        catalog_sample=catalog_sample
    )
    
    client = get_client()
    try:
        response = await client.generate_text(full_prompt, model=STRAICO_MODEL)
        # Parse JSON
        cleaned = _clean_json_string(response)
        data = json.loads(cleaned)
        return data.get("options", [])
    except Exception as e:
        print(f"[Brainstormer] Error: {e}")
        return []

async def select_best_transformation(
    brand_bio: BrandBio,
    campaign_goal: str,
    options: List[Dict]
) -> Dict:
    """
    Agent B: Selects the best transformation.
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "campaign_planner" / "transformation_judge.txt"
    template = prompt_path.read_text(encoding="utf-8")
    
    full_prompt = template.format(
        brand_bio=brand_bio.model_dump_json(),
        campaign_goal=campaign_goal,
        options_json=json.dumps(options, indent=2)
    )
    
    client = get_client()
    try:
        response = await client.generate_text(full_prompt, model=STRAICO_MODEL)
        cleaned = _clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        print(f"[Judge] Error: {e}")
        return {}

async def optimize_plan_transformations(
    plan: CampaignPlan,
    brand_bio: BrandBio
) -> CampaignPlan:
    """
    Iterates through the plan and optimizes the transformation for each slot
    using the Brainstorm -> Judge workflow.
    """
    print(f"\n[Transformation Optimizer] Refining transformations for {plan.total_emails} emails...")
    
    for slot in plan.email_slots:
        print(f" - [Slot {slot.slot_number}] Brainstorming...")
        
        # 1. Brainstorm
        options = await brainstorm_transformations(
            brand_bio=brand_bio,
            campaign_goal=plan.campaign_goal,
            product=slot.offer_details or slot.key_message or "General Brand Products",
            purpose=slot.email_purpose,
            structure=slot.structure_id
        )
        
        if not options:
            print(f"   [Warning] Brainstorming failed for Slot {slot.slot_number}. Keeping original.")
            continue
            
        # 2. Judge
        print(f"   - [Slot {slot.slot_number}] Judging {len(options)} options...")
        verdict = await select_best_transformation(brand_bio, plan.campaign_goal, options)
        
        if verdict and verdict.get("final_refined_transformation"):
            # 3. Apply
            new_trans = verdict["final_refined_transformation"]
            rationale = verdict.get("rationale", "N/A")
            print(f"   => WINNER: {new_trans}")
            print(f"      (Rationale: {rationale})")
            
            slot.transformation_description = new_trans
        else:
            print(f"   [Warning] Judging failed for Slot {slot.slot_number}. Keeping original.")

    return plan

def _clean_json_string(raw_text: str) -> str:
    """Helper for JSON cleanup"""
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


def get_transformation_options(
    brand_name: str,
    campaign_goal: str,
    exclude_recent: bool = True
) -> str:
    """
    Get available transformation options from knowledge base.
    Filters out recently used transformations if exclude_recent=True.
    
    Args:
        brand_name: Brand name for history lookup
        campaign_goal: Campaign goal for context
        exclude_recent: Whether to exclude transformations from last 10 emails
    
    Returns:
        JSON string with transformation options and recommendations
    """
    # Get transformations from knowledge base
    transformations_content = knowledge_reader.get_document_content("Transformations v2.pdf")
    
    # Get recent history
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=10) if exclude_recent else []
    used_transformations = [entry.transformation_used for entry in recent_history]
    
    result = {
        "available_transformations": transformations_content[:2000],  # Truncate for context
        "recently_used": used_transformations,
        "recommendation": f"Choose transformations that align with '{campaign_goal}' and avoid: {', '.join(used_transformations[:5])}"
    }
    
    import json
    return json.dumps(result, indent=2)

def get_storytelling_angle_options(
    brand_name: str,
    email_purpose: str,
    exclude_recent: bool = True
) -> str:
    """
    Get available storytelling angle options from knowledge base.
    
    Args:
        brand_name: Brand name for history lookup
        email_purpose: Purpose of email (promotional, educational, etc.)
        exclude_recent: Whether to exclude angles from last 10 emails
    
    Returns:
        JSON string with storytelling angle options
    """
    # Get storytelling angles from knowledge base
    storytelling_content = knowledge_reader.get_document_content("Storytelling.pdf")
    
    # Get recent history
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=10) if exclude_recent else []
    used_angles = [entry.storytelling_angle_used for entry in recent_history]
    
    result = {
        "available_angles": storytelling_content[:2000],
        "recently_used": used_angles,
        "recommendation": f"For {email_purpose} emails, choose angles that haven't been used recently: avoid {', '.join(used_angles[:5])}"
    }
    
    import json
    return json.dumps(result, indent=2)

def get_structure_options(
    brand_name: str,
    transformation: str,
    exclude_recent: bool = True
) -> str:
    """
    Get available structure options from knowledge base.
    
    Args:
        brand_name: Brand name for history lookup
        transformation: The transformation for this email (for context)
        exclude_recent: Whether to exclude structures from last 5 emails
    
    Returns:
        JSON string with structure options
    """
    # Get structures from knowledge base
    structures_content = knowledge_reader.get_document_content("Email Descriptive Block Structures_ A Comprehensive Guide.pdf")
    
    # Get recent history
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=5) if exclude_recent else []
    used_structures = [entry.structure_used for entry in recent_history]
    
    result = {
        "available_structures": structures_content[:2000],
        "recently_used": used_structures,
        "recommendation": f"Choose a structure that fits '{transformation}' and avoid: {', '.join(used_structures)}"
    }
    
    import json
    return json.dumps(result, indent=2)

def get_persona_options(
    brand_name: str,
    target_audience: str
) -> str:
    """
    Get available persona options from knowledge base.
    
    Args:
        brand_name: Brand name for context
        target_audience: Target audience description
    
    Returns:
        JSON string with persona options
    """
    # Get personas from knowledge base
    personas_content = knowledge_reader.get_document_content("Personas.pdf")
    
    result = {
        "available_personas": personas_content[:2000],
        "recommendation": f"Choose personas that resonate with '{target_audience}'. Variety is good, but some repetition is acceptable."
    }
    
    import json
    return json.dumps(result, indent=2)

def validate_campaign_variety(
    brand_name: str,
    proposed_slots: List[Dict[str, Any]]
) -> str:
    """
    Validate that proposed email slots have sufficient variety.
    
    Args:
        brand_name: Brand name for history lookup
        proposed_slots: List of email slot dictionaries
    
    Returns:
        JSON string with validation results
    """
    # Check for internal repetition
    transformations = [slot.get("assigned_transformation") for slot in proposed_slots]
    angles = [slot.get("assigned_angle") for slot in proposed_slots]
    structures = [slot.get("assigned_structure") for slot in proposed_slots]
    
    issues = []
    
    # Check for duplicates within the campaign
    if len(transformations) != len(set(transformations)):
        duplicates = [t for t in transformations if transformations.count(t) > 1]
        issues.append(f"Duplicate transformations found: {set(duplicates)}")
    
    if len(angles) != len(set(angles)):
        duplicates = [a for a in angles if angles.count(a) > 1]
        issues.append(f"Duplicate storytelling angles found: {set(duplicates)}")
    
    if len(structures) != len(set(structures)):
        duplicates = [s for s in structures if structures.count(s) > 1]
        issues.append(f"Duplicate structures found: {set(duplicates)}")
    
    # Check against recent history
    recent_history = history_manager.get_recent_campaigns(brand_name, limit=10)
    recent_transformations = [entry.transformation_used for entry in recent_history]
    recent_angles = [entry.storytelling_angle_used for entry in recent_history]
    
    history_conflicts = []
    for t in transformations:
        if t in recent_transformations:
            history_conflicts.append(f"Transformation '{t}' was used recently")
    
    for a in angles:
        if a in recent_angles:
            history_conflicts.append(f"Angle '{a}' was used recently")
    
    result = {
        "valid": len(issues) == 0 and len(history_conflicts) == 0,
        "internal_issues": issues,
        "history_conflicts": history_conflicts,
        "recommendation": "Fix all issues before finalizing the campaign plan" if issues or history_conflicts else "Variety looks good!"
    }
    
    import json
    return json.dumps(result, indent=2)
