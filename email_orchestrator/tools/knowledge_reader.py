import os
from pathlib import Path
from typing import Dict, Optional
from pypdf import PdfReader

class KnowledgeReader:
    """
    Reads and caches the text content of the PDF knowledge base.
    """
    def __init__(self, knowledge_dir: Optional[str] = None):
        if knowledge_dir:
            self.knowledge_dir = Path(knowledge_dir)
        else:
            # Default to email_orchestrator/knowledge relative to this file
            self.knowledge_dir = Path(__file__).parent.parent / "knowledge"
        
        self._cache: Dict[str, str] = {}

    def get_document_content(self, filename: str) -> str:
        """
        Returns the text content of a generic PDF file in the knowledge dir.
        """
        if filename in self._cache:
            return self._cache[filename]

        file_path = self.knowledge_dir / filename
        if not file_path.exists():
            # Try fuzzy match or error
            print(f"[KnowledgeReader] Warning: File {filename} not found.")
            return ""

        try:
            reader = PdfReader(str(file_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            self._cache[filename] = text
            return text
        except Exception as e:
            print(f"[KnowledgeReader] Error reading {filename}: {e}")
            return ""

    def get_all_context(self) -> str:
        """
        Helper to get a combined context string of the key PDFs for the Strategist.
        """
        files = [
            "Transformations v2.pdf",
            "Email Descriptive Block Structures_ A Comprehensive Guide.pdf",
            "Personas.pdf",
            "Storytelling.pdf",
            "Offer.pdf"
        ]
        
        combined_text = ""
        for f in files:
            content = self.get_document_content(f)
            combined_text += f"\n\n=== {f} ===\n{content}"
            
        return combined_text
