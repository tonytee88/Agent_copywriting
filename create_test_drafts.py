
import json
import os
from datetime import datetime

def create_table_drafts():
    html_table_1 = """
    <table>
        <tr><td><strong>Feature</strong></td><td><strong>Benefit</strong></td></tr>
        <tr><td>Hydration</td><td>Keeps skin moist</td></tr>
    </table>
    """
    
    html_table_2 = """
    <table>
        <tr><td><strong>Step</strong></td><td><strong>Action</strong></td></tr>
        <tr><td>1</td><td>Open Bottle</td></tr>
        <tr><td>2</td><td>Drink</td></tr>
        <tr><td>3</td><td>Enjoy</td></tr>
    </table>
    """
    
    html_table_3 = """
    <table>
        <tr><td><strong>Day</strong></td><td><strong>Goal</strong></td></tr>
        <tr><td>Mon</td><td>1L</td></tr>
        <tr><td>Tue</td><td>1.5L</td></tr>
        <tr><td>Wed</td><td>2L</td></tr>
    </table>
    """
    
    drafts = []
    
    for i, content in enumerate([html_table_1, html_table_2, html_table_3], 1):
        drafts.append({
            "slot_number": i,
            "status": "completed",
            "subject": f"Test Email {i} with Table",
            "preview": f"Preview for {i}",
            "hero_title": f"Hero {i}",
            "hero_subtitle": f"Subtitle {i}",
            "descriptive_block_title": f"Desc Title {i}",
            "descriptive_block_subtitle": f"Desc Subtitle {i}",
            "descriptive_block_content": content,
            "products": [f"Prod {i}-A", f"Prod {i}-B"],
            "language": "EN"
        })
        
    path = os.path.join("outputs", "drafts", "test_tables.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(drafts, f, indent=2)
        
    print(f"Created {path}")

if __name__ == "__main__":
    create_table_drafts()
