
from email_orchestrator.tools.html_to_docs_parser import HtmlToDocsParser

def debug_specific_string():
    parser = HtmlToDocsParser()
    text = "<b>Offre exclusive</b> : Pack Confort"
    
    print(f"Input: {text}")
    ops = parser.parse_to_ops(text)
    
    for op in ops:
        if op['type'] == 'text':
            print(f"Clean Text: '{op['data']['text']}'")
            print(f"Styles: {op['data']['styles']}")
        else:
            print(f"Op Type: {op['type']}")

if __name__ == "__main__":
    debug_specific_string()
