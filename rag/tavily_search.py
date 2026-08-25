import json
import urllib.request
from typing import Dict, Any, List
import config

class TavilySearcher:
    """Handles fallback web searches using the Tavily API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.TAVILY_API_KEY
        self.endpoint = config.TAVILY_SEARCH_URL

    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Executes a web search with Tavily to find fallback documentation.
        Appends context keywords to the query to restrict it to POS topics.
        """
        if not self.api_key:
            return {
                "error": "Tavily API key is not configured.",
                "results": []
            }

        # Enhance query with context bounds to reduce noise
        scoped_query = f"{query} LOC SMS POS Verifone Buypass Fiserv"

        payload = {
            "api_key": self.api_key,
            "query": scoped_query,
            "search_depth": "basic",
            "max_results": top_k,
            "include_answer": False
        }

        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            return {
                "results": result.get("results", []),
                "error": None
            }
        except Exception as e:
            return {
                "results": [],
                "error": f"Tavily Search API Error: {str(e)}"
            }

    def format_results_as_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Formats the web search snippets into a context block for the LLM."""
        if not search_results:
            return ""
            
        blocks = []
        for idx, result in enumerate(search_results):
            title = result.get("title", "Unknown Title")
            url = result.get("url", "Unknown URL")
            content = result.get("content", "").strip()
            
            blocks.append(
                f"--- [Web Source #{idx+1} | Title: {title} | URL: {url}] ---\n{content}\n"
            )
            
        return "\n".join(blocks)
