
import html
from email_orchestrator.tools.html_to_docs_parser import HtmlToDocsParser

def test_parser():
    parser = HtmlToDocsParser()
    
    print("--- Test 1: Minimal Table (Raw) ---")
    raw_table = "<table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>"
    ops = parser.parse_to_ops(raw_table)
    print(f"Ops count: {len(ops)}")
    print(f"Op Type: {ops[0]['type'] if ops else 'None'}")
    
    print("\n--- Test 2: Minimal Table (Escaped) ---")
    escaped_table = "&lt;table&gt;&lt;tr&gt;&lt;td&gt;Cell 1&lt;/td&gt;&lt;td&gt;Cell 2&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;"
    ops = parser.parse_to_ops(escaped_table)
    print(f"Ops count: {len(ops)}")
    if ops:
        print(f"Op Type: {ops[0]['type']}")
        if ops[0]['type'] == 'text':
             print(f"Text content: '{ops[0]['data']['text']}'")
    
    print("\n--- Test 3: Bold Tags (Escaped) ---")
    escaped_bold = "&lt;b&gt;Offre exclusive&lt;/b&gt; : Pack Confort"
    ops = parser.parse_to_ops(escaped_bold)
    if ops:
        print(f"Text: {ops[0]['data']['text']}")
        print(f"Styles: {ops[0]['data']['styles']}")

if __name__ == "__main__":
    test_parser()
