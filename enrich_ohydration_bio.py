import json
import os
from pathlib import Path

# Data based on the user's Plomberie Mascouche example but adapted for Ohydration
# This focuses on "Hydration Powder" vs "Recipes"

enhanced_bio = {
    "brand_id": "ohydration.com",
    "website_url": "https://ohydration.com",
    "brand_name": "Ohydration",
    "industry": "Health & Wellness / Beverage",
    
    # ========== PRODUCTS / SERVICES ==========
    "category": "D2C E-commerce",
    "product_description": "We sell high-quality hydration powder sachets (electrolytes) that you mix with water. NO recipes, NO cooking. Just tear, pour, shake, and drink.",
    "key_products": [
        "Hydration Powder Sachets (Citrus, Berry, Mint)",
        "Reusable Water Bottles",
        "Starter Kits (Powder + Bottle)"
    ],
    "key_features": [
        "3x more electrolytes than water alone",
        "Zero sugar, naturally sweetened with Stevia",
        "Dissolves instantly in cold water",
        "Travel-friendly single-serve sachets"
    ],
    
    # ========== CONTENT GUARDRAILS (CRITICAL) ==========
    "avoid_topics": [
        "cooking recipes",
        "homemade smoothies",
        "food preparation",
        "meal replacement",
        "DIY hydration mixtures",
        "sugar-filled sports drinks"
    ],
    
    # ========== TARGET AUDIENCE ==========
    "target_audience": "Active families and busy professionals",
    "primary_personas": [
        {
            "name": "Busy Parents (30-45)",
            "description": "Want healthy hydration for their kids without sugar. Need convenience."
        },
        {
            "name": "Fitness Enthusiasts (20-40)",
            "description": "Need effective electrolyte replenishment after workouts without chemicals."
        }
    ],
    "buying_behaviors": [
        "Buys in bulk (30-pack) to save money",
        "Subscribes for monthly delivery",
        "Responds to 'Free Shipping' offers"
    ],
    "values_and_motivations": [
        "Health (clean ingredients)",
        "Convenience (on-the-go)",
        "Taste (must be delicious but not artificial)"
    ],
    
    # ========== BRAND VOICE & STYLE ==========
    "brand_voice": "Energetic, Refreshing, Family-Oriented, Healthy",
    "communication_style": "Clear, encouraging, educational but fun. Uses emojis. Focuses on 'Easy & Effective'.",
    
    # ========== DIFFERENTIATION ==========
    "unique_selling_proposition": "The cleanest family hydration: Science-backed electrolytes with zero sugar and 100% natural taste.",
    "differentiation_elements": [
        "No artificial dyes (clear liquid)",
        "Kid-safe formula",
        "Eco-friendly packaging"
    ],
    
    "pain_points_and_challenges": [
        "Kids hate drinking plain water",
        "Sports drinks are full of sugar",
        "Dehydration causes headaches and fatigue"
    ],
    
    "mission_statement": "To make hydration healthy, delicious, and accessible for the whole family.",
    
    "social_proof": "4.9/5 stars from 500+ reviews. 'My kids finally drink water!' - Sarah T."
}

# Ensure directory exists
os.makedirs("catalogs/brands", exist_ok=True)

# Save the file
output_path = "catalogs/brands/ohydration.com.json" # ID-based filename
with open(output_path, "w") as f:
    json.dump(enhanced_bio, f, indent=4, ensure_ascii=False)

print(f"✓ Created enhanced BrandBio at {output_path}")
