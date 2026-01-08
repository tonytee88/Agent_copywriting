import json
import os

CATALOG_DIR = "catalogs/brands"

def load_bio(filename):
    path = os.path.join(CATALOG_DIR, filename)
    with open(path, 'r') as f:
        return json.load(f)

def save_bio(filename, data):
    path = os.path.join(CATALOG_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✓ Updated {filename}")

def enrich():
    # 1. AMPLOCK
    try:
        amp = load_bio("amplock.com.json")
        amp["primary_personas"] = [
            {"name": "The RV Owner", "description": "Retiree or family man who invested $50k+ in a trailer and is terrified of it being stolen from the driveway."},
            {"name": "The Tradesman", "description": "Contractor with $20k of tools in a cargo trailer. Needs absolute security for livelihood."},
            {"name": "The Boat Owner", "description": "Seasonal user who leaves the boat unattended at the marina or cottage for weeks."}
        ]
        amp["pain_points_and_challenges"] = [
            "Fear of waking up to an empty driveway",
            "Cheap locks can be cut in seconds with bolt cutters",
            "Insurance deductibles are high and claims are a hassle"
        ]
        amp["avoid_topics"] = [
            "GPS tracking (we are mechanical)",
            "Cheap/Plastic materials",
            "Subscription fees",
            "Cloud/App features"
        ]
        amp["communication_style"] = "Robust, Serious, Reassuring. Use words like 'Fortress', 'Invincible', 'Heavy-duty'."
        save_bio("amplock.com.json", amp)
    except FileNotFoundError:
        print("Skipping Amplock (not found)")

    # 2. OHYDRATION
    try:
        ohy = load_bio("ohydration.com.json")
        ohy["pain_points_and_challenges"] = [
            "Kids refusing to drink plain water (dehydration risk)",
            "Commercial sports drinks are full of sugar and dyes",
            "Afternoon energy slumps due to poor hydration",
            "Difficulty swallowing pills (vitamins)"
        ]
        ohy["communication_style"] = "Energetic, Sunny, Encouraging. Uses emojis (💧✨🍊). Focus on 'Easy', 'Yum', 'Happy'."
        # Ensure avoid_topics is strict
        ohy["avoid_topics"] = [
            "Recipes or cooking (It's a drink mix!)",
            "Complex preparation",
            "Medical claims (cure diseases)"
        ]
        save_bio("ohydration.com.json", ohy)
    except FileNotFoundError:
        print("Skipping Ohydration (not found)")

    # 3. POPBRUSH
    try:
        pop = load_bio("popbrush.fr.json")
        pop["pain_points_and_challenges"] = [
            "Morning screaming matches with kids during hair brushing",
            "Time wasted fighting with knots before school",
            "Sensitive scalps that hurt with regular brushes",
            "Hair breakage and split ends from aggressive detangling"
        ]
        pop["buying_behaviors"] = [
            "Impulse buy driven by emotional video ads (crying vs happy child)",
            "Buys bundles (one for home, one for bag)",
            "High sensitivity to 'Pain-Free' promise"
        ]
        pop["communication_style"] = "Empathetic, Gentle, community-focused. Uses 'Moms', 'Little princess', 'Magic'. Lots of testimonials."
        # Add specific avoid
        pop["avoid_topics"] = [
            "Heat styling (it's a detangler, not a straightener)",
            "Chemical treatments",
            "Complicated salon terminology"
        ]
        save_bio("popbrush.fr.json", pop)
    except FileNotFoundError:
        print("Skipping Popbrush (not found)")

if __name__ == "__main__":
    enrich()
