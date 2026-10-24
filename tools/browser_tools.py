"""Web navigation, free knowledge retrieval, and search automation tools for TARS."""
import webbrowser
import urllib.parse
import urllib.request
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional


def open_url(url: str) -> Dict[str, Any]:
    """
    Opens a URL in the user's default web browser.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        webbrowser.open(url)
        return {"success": True, "message": f"Opened {url} in browser."}
    except Exception as e:
        return {"success": False, "error": f"Failed to open {url}: {str(e)}"}


def get_free_knowledge(query: str) -> Optional[str]:
    """
    100% free knowledge retrieval using DuckDuckGo Instant Answer and Wikipedia REST API.
    Requires ZERO API keys, has zero rate limits, and returns instant answers.
    """
    clean_q = query.strip()
    # Strip question preambles
    import re
    clean_q = re.sub(r"^(?:who is|what is|tell me about|explain|where is|search for)\s+", "", clean_q, flags=re.IGNORECASE).strip(" ?.")

    # 1. Try DuckDuckGo Instant Answer API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(clean_q)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(ddg_url, headers={"User-Agent": "TARS-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("AbstractText"):
                return data["AbstractText"]
            if data.get("Answer"):
                return data["Answer"]
    except Exception:
        pass

    # 2. Try Wikipedia Summary API
    try:
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote_plus(clean_q)}"
        req = urllib.request.Request(wiki_url, headers={"User-Agent": "TARS-Agent/1.0 (contact@tars.local)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("extract"):
                return data["extract"]
    except Exception:
        pass

    return None


def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Searches the web via DuckDuckGo & Wikipedia (100% free, zero cost, no keys required).
    """
    # Check free instant knowledge first
    instant_ans = get_free_knowledge(query)
    if instant_ans:
        return {
            "success": True,
            "query": query,
            "answer": instant_ans,
            "results": [{"title": query, "snippet": instant_ans, "url": "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(query)}]
        }

    # Fallback to browser search
    encoded_query = urllib.parse.quote_plus(query)
    try:
        webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
        return {
            "success": True,
            "query": query,
            "results": [],
            "message": f"Opened Google search for '{query}' in your default browser."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to search web: {e}"}


def fetch_webpage_summary(url: str, max_chars: int = 3000) -> Dict[str, Any]:
    """
    Extracts readable text content from a web page without requiring any API keys.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [Truncated]"

        return {
            "success": True,
            "url": url,
            "title": soup.title.string.strip() if soup.title else "Untitled",
            "content": text
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch content from {url}: {str(e)}"}
