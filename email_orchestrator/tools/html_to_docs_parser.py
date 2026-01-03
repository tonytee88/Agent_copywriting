import re
import html
from typing import List, Dict, Any, Tuple

class HtmlToDocsParser:
    """
    Parses HTML-like constraints (tables, lists, bold) from Straico output
    and converts them into Google Docs API batch requests.
    
    Supported Tags:
    - <table>, <tr>, <td>
    - <ul>, <li>
    - <b>, <strong>
    - <br>, <p>
    - <blockquote>
    """
    
    def parse_to_ops(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parses HTML into a list of high-level operations.
        Returns list of dicts: {'type': 'text|table|list', ...}
        """
        ops = []
        
        # 1. Split by Table to isolate complex blocks
        parts = re.split(r'(<table.*?>.*?</table>)', html_content, flags=re.DOTALL)
        
        for part in parts:
            if not part: continue
            
            if part.strip().startswith('<table'):
                ops.append(self._parse_table_op(part))
            else:
                # Process text/lists
                ops.extend(self._parse_text_ops(part))
                
        return ops

    def _parse_table_op(self, table_html: str) -> Dict[str, Any]:
        """Parses a table block into a structured OpTable."""
        rows_html = re.findall(r'<tr.*?>(.*?)</tr>', table_html, flags=re.DOTALL)
        if not rows_html: return {'type': 'text', 'content': ''}
        
        grid = []
        for row_html in rows_html:
            cols_html = re.findall(r'<td.*?>(.*?)</td>', row_html, flags=re.DOTALL)
            # Parse content of each cell (it might contain bold tags)
            row_data = [self._clean_text_content(col) for col in cols_html]
            grid.append(row_data)
            
        return {
            'type': 'table',
            'rows': len(grid),
            'columns': len(grid[0]) if grid else 0,
            'cells': grid # List of Lists of cleaned textual/style data
        }

    def _parse_text_ops(self, html_text: str) -> List[Dict[str, Any]]:
        """Parses mixed text/lists into ops."""
        ops = []
        parts = re.split(r'(<ul.*?>.*?</ul>)', html_text, flags=re.DOTALL)
        
        for part in parts:
            if not part: continue
            
            if part.strip().startswith('<ul'):
                # List Block
                items = re.findall(r'<li.*?>(.*?)</li>', part, flags=re.DOTALL)
                clean_items = [self._clean_text_content(item) for item in items]
                ops.append({
                    'type': 'list',
                    'items': clean_items
                })
            else:
                # Text Block
                # Clean generic tags that we don't support special ops for
                clean_data = self._clean_text_content(part)
                # If there's content or it's just newlines
                if clean_data['text']:
                    ops.append({
                        'type': 'text',
                        'data': clean_data
                    })
        return ops

    def _clean_text_content(self, html_snippet: str) -> Dict[str, Any]:
        """
        Robust text cleaner.
        1. Handle Lists/Tables/BR to newlines.
        2. Strip unknown tags.
        3. Collapse whitespace.
        4. Parse Bold/Italic/Underline.
        """
        # 0. Decode HTML entities
        text = html.unescape(html_snippet)
        
        # 1. Normalize line breaks and spaces
        # Replace explicit block tags with placeholders
        text = re.sub(r'<br\s*/?>', '__BR__', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '__BR__', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '__BR__', text, flags=re.IGNORECASE)
        text = re.sub(r'<li.*?>', '__LI__', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '__BR__', text, flags=re.IGNORECASE)
        text = re.sub(r'</blockquote>', '__BR__', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '__BR__', text, flags=re.IGNORECASE) # Just in case

        # 2. Strip all tags EXCEPT formatting (b, i, u, strong, em)
        # Use a negative lookahead regex
        text = re.sub(r'<(?!/?(b|i|u|strong|em)\b).*?>', '', text, flags=re.IGNORECASE)
        
        # 3. Collapse multiple spaces/tabs into single space (but keep placeholders)
        # We replace any sequence of whitespace chars with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # 4. Restore Placeholders
        text = text.replace('__BR__', '\n')
        text = text.replace('__LI__', '\n• ') # Fake bullet for table cells
        
        # 5. Fix double newlines and trim
        text = re.sub(r'\n\s*\n', '\n', text)
        text = text.strip()

        # 6. Extract Styles (Bold, Italic, Underline)
        final_text = ""
        styles = []
        
        # Split by known tags
        tokens = re.split(r'(</?[biuBIU].*?>|<strong>|</strong>|<em>|</em>)', text)
        
        current_style = {'bold': False, 'italic': False, 'underline': False}
        curr_idx = 0
        
        for token in tokens:
            if not token: continue
            
            lower = token.lower()
            
            # Start Tags
            if re.match(r'<b\b|<strong>', lower):
                current_style['bold'] = True
            elif re.match(r'<i\b|<em>', lower):
                current_style['italic'] = True
            elif re.match(r'<u\b', lower):
                current_style['underline'] = True
                
            # End Tags
            elif re.match(r'</b>|</strong>', lower):
                current_style['bold'] = False
            elif re.match(r'</i>|</em>', lower):
                current_style['italic'] = False
            elif re.match(r'</u>', lower):
                current_style['underline'] = False
                
            # Content
            else:
                # It's text content. 
                # Since we already stripped unknown tags in step 2, this is pure text.
                content = token
                if content:
                    length = len(content)
                    start = curr_idx
                    end = curr_idx + length
                    
                    if current_style['bold']:
                        styles.append({'start': start, 'end': end, 'type': 'bold'})
                    if current_style['italic']:
                        styles.append({'start': start, 'end': end, 'type': 'italic'})
                    if current_style['underline']:
                        styles.append({'start': start, 'end': end, 'type': 'underline'})
                    
                    final_text += content
                    curr_idx += length
        
        return {
            'text': final_text,
            'styles': styles
        }
        
    def _process_rich_text(self, text: str, end_newline: bool = False):
        """
        Handles <b>, <br>, <blockquote>, <p>
        and converts to 'text' instructions.
        """
        # Converts to internal instruction format
        # For simplicity in this task, let's output a unified instruction list
        # instructions: List[Dict] = [{'type': 'text', 'content': 'foo', 'bold': True}, {'type': 'newline'}]
        pass

