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
        Converts 'Hello <b>World</b>' into:
        {'text': 'Hello World', 'styles': [{'start': 6, 'end': 11, 'bold': True}]}
        Also handles <br>, <p> by converting to newlines.
        Now supports <i> and <u>.
        """
        # 0. Decode HTML entities (e.g. &nbsp; -> ' ')
        html_snippet = html.unescape(html_snippet)
        
        # 1. Replace block tags with newlines
        text = re.sub(r'<br\s*/?>', '\n', html_snippet)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<p.*?>', '', text)
        text = re.sub(r'<blockquote>', '\n" ', text)
        text = re.sub(r'</blockquote>', ' "\n', text)
        
        # 2. Extract Styles (Bold, Italic, Underline)
        # We need a robust state machine or strict regex replacement to handle multiple tags
        # For simplicity (and since Stylist is instructed to use simple tags), we track tags by index.
        # But regex split is tricky for multiple types.
        
        # Strategy: Use a simple state parser or perform multiple passes?
        # Multiple passes is hard because indices shift.
        # Better: Tokenize by ANY tag.
        
        final_text = ""
        styles = []
        
        # Split by any tag
        tokens = re.split(r'(</?[biuBIU].*?>|<strong>|</strong>|<em>|</em>)', text)
        
        # Stack for active styles: {'bold': bool, 'italic': bool, 'underline': bool}
        current_style = {'bold': False, 'italic': False, 'underline': False}
        
        # We need to track where styles START
        # style_starts = {'bold': None, 'italic': None, 'underline': None}
        # But this doesn't handle nesting well if we just blindly append ranges.
        # Actually, flattening styles to ranges is fine.
        
        # Easier: Process token by token. If content, append to final_text and record current VALID styles.
        # But we need "Ranges".
        # So if we are in 'bold' mode, and we add text of len 5, we add range [curr, curr+5, bold=True]
        
        curr_idx = 0
        
        for token in tokens:
            if not token: continue
            
            lower = token.lower()
            
            # Start Tags
            if lower in ['<b>', '<strong>']:
                current_style['bold'] = True
            elif lower in ['<i>', '<em>']:
                current_style['italic'] = True
            elif lower in ['<u>']:
                current_style['underline'] = True
                
            # End Tags
            elif lower in ['</b>', '</strong>']:
                current_style['bold'] = False
            elif lower in ['</i>', '</em>']:
                current_style['italic'] = False
            elif lower in ['</u>']:
                current_style['underline'] = False
                
            # Content
            elif not re.match(r'<.*?>', token):
                # Clean any other rogue tags inside token (unlikely with split, but possible)
                content = token # re.sub(r'<.*?>', '', token) # Should be clean
                length = len(content)
                if length > 0:
                    start = curr_idx
                    end = curr_idx + length
                    
                    # Record styles for this chunk
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

