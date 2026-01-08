import json
import os

CATALOG_DIR = "catalogs/brands"

def update_json(filename, updates):
    path = os.path.join(CATALOG_DIR, filename)
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        # recursive update or simple key overwrite? Simple is safter for now.
        for key, value in updates.items():
            data[key] = value
            
        with open(path, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✓ Enriched {filename}")
    except FileNotFoundError:
        print(f"⚠ File {filename} not found.")

def run_enrichment():
    # ================= AMPLOCK =================
    update_json("amplock.com.json", {
        "key_features": [
            "Made from ductile cast iron and stainless steel for maximum impact resistance",
            "Rotating disc tumbler mechanism (bump-proof and pick-resistant)",
            "Push-and-lock cylinder for keyless locking convenience",
            "Rust-resistant E-coat and electrostatic paint finish",
            "5-Year Warranty against manufacturing defects"
        ],
        "competitive_analysis": "Primary competitors include Proven Industries, PACLOCK, and Master Lock. AMPLock differentiates via its specific 'ductile iron' construction which resists liquid nitrogen and torching better than standard hardened steel, and its millions of key combinations.",
        "social_proof": "Over 250,000 satisfied customers in North America. Rated 4.7/5 stars on Amazon.",
        "unique_selling_proposition": "The ultimate mechanical fortress for your trailer: Premium North American ductile iron construction that stops thieves cold, backed by a 5-year warranty."
    })

    # ================= OHYDRATION =================
    update_json("ohydration.com.json", {
        "key_features": [
            "Zero Sugar & Zero Artificial Sweeteners (No Sucralose/Aspartame)",
            "Sweetened naturally with Stevia and fruit extracts",
            "Formulated with Biotin (B7) and Vitamin E for hair/skin health",
            "Low calorie (10-15 cal per serving)",
            "Vegan, Gluten-Free, and Keto-friendly"
        ],
        "brand_history": "Founded by Cassandra after her personal struggle to find healthy hydration without the 'chemical cocktail' of red dyes and artificial sweeteners found in mainstream sports drinks.",
        "competitive_analysis": "Competes with Liquid I.V., BioSteel, and Gatorade. Differentiates by strictly avoiding 'dirty' ingredients like Red Dye 40 and artificial sweeteners while maintaining a lower price point per serving.",
        "social_proof": "Over 56,000 customers. Rated 'Excellent' for taste compared to salty competitors.",
        "product_description": "Natural vitaminized water powder sachets. Just tear, pour into water, and shake. Contains electrolytes (Potassium/Sodium) plus a beauty/energy vitamin boost (B-Complex, Vitamin E)."
    })

    # ================= POPBRUSH =================
    update_json("popbrush.fr.json", {
        "key_features": [
            "Hybrid Bristle Technology: Natural Boar Bristles (for shine) + Nylon Pins (for detangling)",
            "Curved shape matches head contour for scalp massage",
            "Vented design for faster blow-drying",
            "Works on wet or dry hair without breakage",
            "Reduces brushing time by up to 66%"
        ],
        "competitive_analysis": "Main competitors: Wet Brush (often lacks boar bristles), Tangle Teezer (plastic only), Mason Pearson (high price). PopBrush offers the 'Boar+Nylon' combo at an accessible price point, specifically targeting the 'pain-free' mom/kid niche.",
        "social_proof": "Trusted by 187,000+ users. 4.4/5 rating on Trustpilot. Famous for 'ending morning screaming matches'.",
        "differentiation_elements": [
            "Boar bristles distribute natural scalp oils for shiny hair",
            "Pain-free promise specifically for sensitive scalps",
            "Ergonomic curved design unlike flat paddle brushes"
        ]
    })

if __name__ == "__main__":
    run_enrichment()
