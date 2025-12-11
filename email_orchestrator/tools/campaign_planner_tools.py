"""
Helper tools for the Campaign Planner ADK Agent.
These tools provide contextual suggestions for strategic content selection.
"""

from typing import List, Dict, Any
from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager

# Initialize tools
knowledge_reader = KnowledgeReader()
history_manager = HistoryManager()

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
