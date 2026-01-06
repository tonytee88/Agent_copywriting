
from email_orchestrator.tools.html_to_docs_parser import HtmlToDocsParser

def test_parser_drafts():
    parser = HtmlToDocsParser()
    
    # Email 2 Content (Paragraphs)
    email2_content = "<p><b>Hydratation quotidienne :</b> Privil\u00e9giez des soins adapt\u00e9s pour \u00e9viter la s\u00e9cheresse.</p><br>\n\n<p><b>Accessoires PopBrush :</b> Utilisez les brosses d\u00e9m\u00ealantes pour limiter la casse et faciliter le coiffage.</p>"
    print("\n--- Email 2 (Paragraphs) ---")
    ops = parser.parse_to_ops(email2_content)
    print(f"Ops count: {len(ops)}")
    for i, op in enumerate(ops):
        print(f"Op {i} Type: {op['type']}")
        if op['type'] == 'text':
             print(f"Text: '{op['data']['text'][:50]}...'")

    # Email 3 Content (UL List)
    email3_content = "<ul>\n<li>\u2728 <b>Routine simplifi\u00e9e</b> : Fini les cris et les noeuds chaque matin.</li>\n<li>\u2728 <b>Gain de temps</b> : Cheveux parfaitement d\u00e9m\u00eal\u00e9s en quelques minutes.</li></ul>"
    print("\n--- Email 3 (List) ---")
    ops = parser.parse_to_ops(email3_content)
    print(f"Ops count: {len(ops)}")
    for i, op in enumerate(ops):
        print(f"Op {i} Type: {op['type']}")
        if op['type'] == 'list':
             print(f"Items: {len(op['items'])}")
             print(f"Item 1: '{op['items'][0]['text']}'")

if __name__ == "__main__":
    test_parser_drafts()
