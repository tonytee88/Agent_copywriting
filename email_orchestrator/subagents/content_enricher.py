import json
from datetime import datetime
from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.config import MODEL_RESEARCHER

class ContentEnricher:
    """
    Uses Perplexity (Online LLM) to find real-world data (Stats, Reviews) 
    to support specific email structures.
    """
    
    def __init__(self):
        self.client = get_client()
        self.model = MODEL_RESEARCHER
        
    async def find_stats(self, brand_name: str, product_context: str) -> str:
        """
        Finds quantitative statistics for the brand.
        Returns a formatted string list of stats.
        """
        print(f"[ContentEnricher] Hunting for STATS for {brand_name}...")
        
        prompt = f"""
        TASK: Search online for specific numeric statistics about '{brand_name}' ({product_context}).
        
        OUTPUT FORMAT: JSON List of Strings only.
        
        REQUIREMENTS:
        - Find 8 specific numbers (percentages, ratings, counts, timestamps).
        - Focus on Performance, Ratings (e.g. 4.8/5), or Volume (e.g. 50k+ sold).
        - Verify specific numbers from their website or reviews.
        
        Example:
        ["4.9/5 average rating", "Reduces styling time by 60%", "Used by 500+ salons"]
        """
        
        # Retry Loop for Robustness
        for attempt in range(2):
            try:
                response = await self.client.generate_text(prompt, model=self.model)
                response = response.strip()
                
                # Cleanup Code Blocks
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0]
                
                if "[" in response:
                    response = response[response.find("["):response.rfind("]")+1]
                
                stats_list = json.loads(response)
                
                formatted_out = "REAL-WORLD STATISTICS FOUND (Pick the best 3):\n"
                for stat in stats_list:
                    formatted_out += f"- {stat}\n"
                    
                return formatted_out
            except Exception as e:
                print(f"[ContentEnricher] Stats lookup attempt {attempt+1} failed: {e}")
        
        return "No real-time stats found. Please use generic estimations based on Brand Bio."

    async def find_reviews(self, brand_name: str, product_context: str) -> str:
        """
        Finds authentic reviews/testimonials.
        """
        print(f"[ContentEnricher] Hunting for REVIEWS for {brand_name}...")
        
        prompt = f"""
        TASK: Search online for genuine customer reviews of '{brand_name}' ({product_context}).
        
        OUTPUT FORMAT: JSON List of Objects only.
        fields: text (max 200 chars), author, source, url.
        
        REQUIREMENTS:
        - Find 3 distinct reviews from Amazon, Trustpilot, or verified sites.
        - Include the URL for verification.
        - Positive sentiment.
        
        Example:
        [
          {{"text": "Love this product!", "author": "Jane", "source": "Amazon", "url": "https://amazon.com/..."}}
        ]
        """
        
        for attempt in range(2):
            try:
                response = await self.client.generate_text(prompt, model=self.model)
                response = response.strip()
                print(f"[ContentEnricher DEBUG] Raw Reviews Response: {response[:200]}...")
                
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                   response = response.split("```")[1].split("```")[0]
                
                if "[" in response:
                    response = response[response.find("["):response.rfind("]")+1]
                
                reviews_list = json.loads(response)
                
                formatted_out = "REAL-WORLD REVIEWS FOUND (Pick the best one):\n"
                for rev in reviews_list:
                    url_str = f" [Link: {rev.get('url', 'N/A')}]" if rev.get('url') else ""
                    formatted_out += f"- \"{rev['text']}\" — {rev['author']} ({rev['source']}){url_str}\n"
                    
                return formatted_out
            except Exception as e:
                print(f"[ContentEnricher] Reviews lookup attempt {attempt+1} failed. Error: {e}")
                
        return "No specific reviews found. Please use a generic placeholder."
