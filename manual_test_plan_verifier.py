
import json
from datetime import datetime
from email_orchestrator.tools.deterministic_verifier import DeterministicVerifier
from email_orchestrator.schemas import CampaignPlan, EmailSlot

# ==============================================================================
# 🎮 USER PLAYGROUND: MODIFY THIS MOCK PLAN TO TEST THE VERIFIER
# ==============================================================================

MOCK_PLAN = CampaignPlan(
    campaign_id="test_boxing_day_001",
    brand_name="PopBrush",
    brand_id="popbrush.fr",
    campaign_name="Boxing Day Blowout",
    campaign_goal="Clear inventory and drive revenue",
    duration="1 week",
    total_emails=3,
    overarching_narrative="From post-Christmas recovery to New Year glam.",
    promotional_balance="70% promotional, 30% educational",
    created_at=datetime.utcnow().isoformat(),
    
    # --------------------------------------------------------------------------
    # 👇 EDIT THESE SLOTS TO TRIGGER REPETITION ERRORS
    # Try using the same 'structure_id' or 'angle_description' in multiple slots!
    # --------------------------------------------------------------------------
    email_slots=[
        EmailSlot(
            slot_number=1,
            email_purpose="promotional",
            intensity_level="medium",
            
            # Slot 1 Settings
            structure_id="STRUCT_STAT_ATTACK", 
            angle_description="Preparing lasagna",
            transformation_description="From toys to love",
            
            # Other required fields (Ignore for this test)
            theme="Recovery", key_message="Relax", persona_description="Best Friend", cta_description="Shop Sale"
        ),
        
        EmailSlot(
            slot_number=2,
            email_purpose="educational",
            intensity_level="soft",
            
            # Slot 2 Settings: REPEATING STRUCTURE ID from Slot 1
            structure_id="STRUCT_GIF_PREVIEW", 
            angle_description="Prepare for New Year's Eve with the perfect look.",
            transformation_description="From flat hair to voluminous NYE style.",
            
            theme="NYE Prep", key_message="Volume", persona_description="Expert Stylist", cta_description="Get the Look"
        ),
        
        EmailSlot(
            slot_number=3,
            email_purpose="promotional",
            intensity_level="hard_sell",
            
            # Slot 3 Settings: FUZZY ANGLE REPETITION from Slot 1
            structure_id="STRUCT_MINI_GRID",
            angle_description="Emphasizing the the love and food in the fridge", # Very close match 
            transformation_description="From outdated tools to modern efficiency.",
            
            theme="Last Chance", key_message="Urgency", persona_description="Hype Man", cta_description="Buy Now"
        )
    ]
)

# ==============================================================================
# 🧪 TEST RUNNER
# ==============================================================================

def run_test():
    print("\n" + "="*60)
    print("🚦 RUNNING DETERMINISTIC PLAN VERIFIER TEST")
    print("="*60)
    print(f"Plan: {MOCK_PLAN.campaign_name} ({len(MOCK_PLAN.email_slots)} emails)")
    
    verifier = DeterministicVerifier()
    
    # ==============================================================================
    # 📚 REAL HISTORY LOADING
    # ==============================================================================
    from email_orchestrator.tools.history_manager import HistoryManager
    
    print("\n[History Setup] Loading REAL history from email_history_log.json...")
    history_manager = HistoryManager()
    
    # Use brand_id if available, else name
    brand_identifier = MOCK_PLAN.brand_id or MOCK_PLAN.brand_name
    
    # Fetch recent campaigns
    raw_history = history_manager.get_recent_campaigns(brand_identifier, limit=10)
    
    # Convert to dicts for the verifier
    history = [entry.model_dump() for entry in raw_history]
    
    print(f"   > Loaded {len(history)} past campaigns for brand '{brand_identifier}'.")
    if history:
        for i, entry in enumerate(history):
            print(f"     [{i}] ID: {entry.get('campaign_id')} | Date: {entry.get('timestamp')}")
            print(f"         Struct: {entry.get('structure_id')}")
            print(f"         Angle:  {entry.get('angle_description')}")
            print(f"         Trans:  {entry.get('transformation_description')}")
    else:
        print("   > No history found. Verification will skip repetition checks.")
    
    print("\n[Running verify_plan...]")
    issues = verifier.verify_plan(MOCK_PLAN, history)
    
    if not issues:
        print("\n✅ PASSED! Plan is valid.")
        print("   - No internal repetition found.")
        print("   - No history conflicts (either distinct or history is old/empty).")
        print("   - Structure IDs are valid.")
    else:
        print(f"\n❌ FOUND {len(issues)} ISSUES (Should be 0 if logic works):")
        for i, issue in enumerate(issues, 1):
            print(f"\n   ISSUE #{i}:")
            print(f"   [Type] {issue.type}")
            print(f"   [Field] {issue.field}")
            print(f"   [Problem] {issue.problem}")
            print(f"   [Rationale] {issue.rationale}")

if __name__ == "__main__":
    run_test()
