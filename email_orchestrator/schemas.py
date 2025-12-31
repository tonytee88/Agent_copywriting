from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field, model_validator

# --- Brand & Context Schemas ---

class BrandBio(BaseModel):
    """Structured brand information used for context."""
    brand_id: Optional[str] = None # Unique ID (e.g. popbrush.fr)
    website_url: Optional[str] = None
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
    languages: List[str] = ["FR"] # Defaut: FR

# --- Strategist Output / Drafter Input ---

class EmailBlueprint(BaseModel):
    """
    The architectural plan for the email. 
    Decided by Strategist, executed by Drafter.
    """
    brand_name: str = Field(default="Unknown Brand")
    campaign_theme: str
    
    # Step 2: Transformation
    transformation_description: Optional[str] = Field(None, description="Free-text description of the transformation arc")
    transformation_id: Optional[str] = Field(None, description="Legacy Catalog ID")
    
    # Step 3: Structure
    structure_id: str = Field(description="Catalog ID from structures.json")
    structure_execution_map: Dict[str, str] = Field(description="Specific goals for each block (Hero, Descriptive, Product)")
    
    # Step 4: Persona
    persona_description: Optional[str] = Field(None, description="Free-text description of the persona/voice")
    persona_id: Optional[str] = Field(None, description="Legacy Catalog ID")
    
    # Step 5: Storytelling
    angle_description: Optional[str] = Field(None, description="Free-text description of the angle/hook")
    angle_id: Optional[str] = Field(None, description="Legacy Catalog ID")
    
    # Step 6: Offer & CTAs
    offer_details: str
    offer_placement: Literal["Hero", "Story", "Product", "Descriptive"] = "Hero"
    cta_description: Optional[str] = Field(None, description="Free-text description of the CTA style")
    cta_style_id: Optional[str] = Field(None, description="Legacy Catalog ID")
    
    # Step 7: Content Outline (High level)
    subject_ideas: List[str]
    preview_text_ideas: List[str]
    
    key_points_for_descriptive_block: List[str]
    copy_constraints: List[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def migrate_legacy_fields(self):
        # Backfill descriptions from legacy IDs if missing
        if not self.transformation_description and self.transformation_id:
            self.transformation_description = self.transformation_id
        if not self.persona_description and self.persona_id:
            self.persona_description = self.persona_id
        if not self.angle_description and self.angle_id:
            self.angle_description = self.angle_id
        if not self.cta_description and self.cta_style_id:
            self.cta_description = self.cta_style_id
        return self

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
    
    # Reworked Product Block
    product_block_title: str = Field(default="Shop the Collection")
    product_block_subtitle: str = Field(default="Our top picks for you")
    products: List[str] = Field(default_factory=list, description="List of 3 specific products with brief benefits")
    product_block_content: Optional[str] = None # Legacy/Fallback
    
    cta_product: str
    
    full_text_formatted: str # The full email string for easy reading

class CampaignLogEntry(BaseModel):
    """Record of a sent campaign for history tracking."""
    campaign_id: str
    timestamp: str
    brand_id: Optional[str] = None # Added for multi-brand isolation
    brand_name: str
    
    # ID-based tracking for non-repetition logic (Updated to descriptions for free-text)
    transformation_description: Optional[str] = None
    transformation_id: Optional[str] = None  # Legacy
    
    structure_id: str
    
    angle_description: Optional[str] = None
    angle_id: Optional[str] = None # Legacy
    
    cta_description: Optional[str] = None
    cta_style_id: Optional[str] = None # Legacy
    
    offer_placement_used: str
    
    # Optional: Full objects for detailed review (not needed for non-repetition logic)
    # These are excluded from lightweight logging to save 87% storage
    blueprint: Optional[EmailBlueprint] = None
    final_draft: Optional[EmailDraft] = None

    @model_validator(mode='after')
    def migrate_legacy_log_fields(self):
        if not self.transformation_description and self.transformation_id:
            self.transformation_description = self.transformation_id
        if not self.angle_description and self.angle_id:
            self.angle_description = self.angle_id
        if not self.cta_description and self.cta_style_id:
            self.cta_description = self.cta_style_id
        return self

# --- Campaign Planning Schemas ---

class EmailSlot(BaseModel):
    """A single email in the campaign plan."""
    slot_number: int
    send_date: Optional[str] = None  # ISO format or relative like "Day 1"
    email_purpose: Literal["promotional", "educational", "storytelling", "nurture", "conversion"]
    intensity_level: Literal["hard_sell", "medium", "soft"]
    
    # Strategic directives (Free-text except Structure)
    transformation_description: str
    structure_id: str
    angle_description: str
    persona_description: str
    cta_description: str
    
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
    brand_id: Optional[str] = None # Added for multi-brand isolation
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
    language: str = "English" # Deprecated/Reference
    languages: List[str] = ["FR"] # Default FR
    sheet_url: Optional[str] = None # Link to the Google Sheet for this plan
    drive_folder_id: Optional[str] = None # Folder where assets are stored
    
    # Context Propagation
    campaign_context: Optional[str] = None # Raw user input + notes for downstream agents

# --- Verification Schemas ---

class Issue(BaseModel):
    """A specific quality issue detected by QA."""
    type: Literal["repetition", "history_repetition", "balance", "coherence", "completeness", "formatting", "quality", "compliance", "structure_id", "validity", "structure_id_validity", "other"]
    severity: Literal["P1", "P2", "P3"] # P1 = Blocker, P2 = Major, P3 = Minor
    scope: Literal["campaign", "email", "history"]
    email_slot: Optional[int] = None
    field: str
    problem: str
    rationale: str

class BlockingIssue(BaseModel):
    """Legacy strategic blocker (keeping for compat)."""
    category: Literal["offer_alignment", "narrative_ladder", "structure_purpose_fit", "calendar_sanity"]
    description: str
    why_it_matters: str

class TopImprovement(BaseModel):
    """High-impact improvement for the simplified QA process."""
    rank: int
    category: Literal[
        "calendar_sanity", "offer_alignment", "narrative_ladder", "structure_purpose_fit",
        "content_distribution", "visual_hierarchy", "tone_voice", "conversion_flow"
    ]
    problem: str
    why_it_matters: str
    options: Dict[str, str] # {A: ..., B: ...}

class OptimizationOption(BaseModel):
    """Concrete strategic options for a blocking issue (Legacy)."""
    issue_category: str
    options: Dict[str, str] # e.g. {"A": "...", "B": "..."}

class CampaignPlanVerification(BaseModel):
    """Verification result for a campaign plan (Simplified Mode)."""
    approved: bool
    final_verdict: str
    
    # New Standard
    top_improvements: List[TopImprovement] = Field(default_factory=list)
    
    # Legacy Fields (Optional/Deprecated)
    score: int = 0 
    blocking_issues: List[BlockingIssue] = Field(default_factory=list)
    optimization_options: List[OptimizationOption] = Field(default_factory=list)
    variety_check: Dict[str, bool] = Field(default_factory=dict)
    balance_check: Dict[str, bool] = Field(default_factory=dict)
    coherence_check: Dict[str, bool] = Field(default_factory=dict)
    issues: List[Issue] = Field(default_factory=list)
    feedback_for_planner: Optional[str] = None

class DraftReplacementOptions(BaseModel):
    """Ready-to-use replacement copy for Email QA."""
    subject_alternatives: List[str] = Field(default_factory=list)
    preview_alternatives: List[str] = Field(default_factory=list)
    hero_title_alternatives: List[str] = Field(default_factory=list)
    hero_subtitle_alternatives: List[str] = Field(default_factory=list)
    hero_cta_alternatives: List[str] = Field(default_factory=list)
    product_cta_alternatives: List[str] = Field(default_factory=list)
    descriptive_block_rewrite_hint: Optional[str] = None

class EmailVerification(BaseModel):
    """Verification result for a single email draft."""
    approved: bool
    score: int
    critical_issues: List[str] = Field(default_factory=list)
    
    # New Judge+Repair Fields
    top_improvements: List[TopImprovement] = Field(default_factory=list)
    issues: List[Issue] = Field(default_factory=list)
    replacement_options: Optional[DraftReplacementOptions] = None
    
    feedback_for_drafter: str
