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
    
    # For duplication checking
    transformation_used: str
    structure_used: str
    storytelling_angle_used: str
    offer_placement_used: str
    cta_style_used: Optional[str] = None
    
    blueprint: EmailBlueprint
    final_draft: EmailDraft
