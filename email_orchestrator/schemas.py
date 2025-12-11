from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field

# --- Brand & Context Schemas ---

class BrandBio(BaseModel):
    """Structured brand information used for context."""
    brand_name: str
    industry: str
    target_audience: str
    unique_selling_proposition: str
    brand_voice: str
    key_products: List[str] = Field(default_factory=list)
    mission_statement: Optional[str] = None

class CampaignRequest(BaseModel):
    """Initial request from the user."""
    brand_name: str
    offer: str
    theme_angle: str
    transformation: Optional[str] = None
    target_audience: Optional[str] = None # Optional override

# --- Strategist Output / Drafter Input ---

class EmailBlueprint(BaseModel):
    """
    The architectural plan for the email. 
    Decided by Strategist, executed by Drafter.
    """
    brand_name: str = Field(default="Unknown Brand")
    campaign_theme: str
    
    # Step 2: Transformation
    selected_transformation: str = Field(description="The core emotional driver (Have/Feel/AvgDay/Status)")
    
    # Step 3: Structure
    descriptive_structure_name: str = Field(description="Name of the structure from the PDF (e.g. Emoji Checklist)")
    structure_guidelines: List[str] = Field(description="Specific formatting rules for this structure")
    
    # Step 4: Persona
    persona_name: str
    persona_voice_guidelines: str
    
    # Step 5: Storytelling
    storytelling_angle: str = Field(description="The narrative hook (e.g. Confession line)")
    
    # Step 6: Offer
    offer_details: str
    offer_placement: Literal["Hero", "Story", "Product"] = "Hero"
    
    # Step 7: Content Outline (High level)
    subject_ideas: List[str]
    preview_text_ideas: List[str]
    
    key_points_for_descriptive_block: List[str]

# --- Output & Logging ---

class EmailDraft(BaseModel):
    """The final generated email content."""
    subject: str
    preview: str
    hero_title: str
    hero_subtitle: str
    cta_hero: str
    
    descriptive_block_title: str
    descriptive_block_subtitle: str
    descriptive_block_content: str # The main body
    
    product_block_content: str
    cta_product: str
    
    full_text_formatted: str # The full email string for easy reading

class CampaignLogEntry(BaseModel):
    """Record of a sent campaign for history tracking."""
    campaign_id: str
    timestamp: str
    brand_name: str
    
    # For duplication checking (essential fields only)
    transformation_used: str
    structure_used: str
    storytelling_angle_used: str
    offer_placement_used: str
    cta_style_used: Optional[str] = None
    
    # Optional: Full objects for detailed review (not needed for non-repetition logic)
    # These are excluded from lightweight logging to save 87% storage
    blueprint: Optional[EmailBlueprint] = None
    final_draft: Optional[EmailDraft] = None

# --- Campaign Planning Schemas ---

class EmailSlot(BaseModel):
    """A single email in the campaign plan."""
    slot_number: int
    send_date: Optional[str] = None  # ISO format or relative like "Day 1"
    email_purpose: Literal["promotional", "educational", "storytelling", "nurture"]
    intensity_level: Literal["hard_sell", "medium", "soft"]
    
    # Strategic directives
    assigned_transformation: str
    assigned_angle: str
    assigned_persona: str
    assigned_structure: str
    
    # Context
    theme: str
    key_message: str
    connection_to_previous: Optional[str] = None
    connection_to_next: Optional[str] = None
    
    # Offer details (if promotional)
    offer_details: Optional[str] = None
    offer_placement: Optional[Literal["Hero", "Story", "Product"]] = None

class CampaignPlan(BaseModel):
    """Strategic plan for a multi-email campaign."""
    campaign_id: str
    brand_name: str
    campaign_name: str
    campaign_goal: str  # e.g., "Build awareness then drive Black Friday sales"
    
    duration: str  # e.g., "1 month", "2 weeks"
    total_emails: int
    
    # Strategic overview
    overarching_narrative: str
    promotional_balance: str  # e.g., "60% educational, 40% promotional"
    
    # Individual email slots
    email_slots: List[EmailSlot]
    
    # Metadata
    created_at: str
    status: Literal["draft", "approved", "in_progress", "completed"] = "draft"

class CampaignPlanVerification(BaseModel):
    """Verification result for a campaign plan."""
    approved: bool
    score: int  # 0-10
    
    # Specific checks
    variety_check: Dict[str, bool]  # e.g., {"no_repeated_transformations": True}
    balance_check: Dict[str, bool]  # e.g., {"promotional_ratio_ok": True}
    coherence_check: Dict[str, bool]  # e.g., {"logical_flow": True}
    
    critical_issues: List[str]
    suggestions: List[str]
    feedback_for_planner: str
