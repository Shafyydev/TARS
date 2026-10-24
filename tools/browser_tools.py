"""Web navigation and search automation tools for TARS."""
import webbrowser
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List


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


def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Searches the web via DuckDuckGo HTML API and extracts top result links and snippets.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for result in soup.find_all("div", class_="result__body")[:max_results]:
            title_tag = result.find("a", class_="result__snippet")
            link_tag = result.find("a", class_="result__url")
            snippet_tag = result.find("a", class_="result__snippet")

            title = result.find("h2").text.strip() if result.find("h2") else "No Title"
            link = link_tag.get("href", "").strip() if link_tag else ""
            snippet = snippet_tag.text.strip() if snippet_tag else ""

            if link and not link.startswith("http"):
                link = "https://" + link

            results.append({
                "title": title,
                "url": link,
                "snippet": snippet
            })

        if not results:
            # Fallback direct search opening in browser
            webbrowser.open(f"https://www.google.com/search?q={encoded_query}")
            return {
                "success": True,
                "results": [],
                "message": f"Opened Google search for '{query}' directly in browser."
            }

        return {"success": True, "query": query, "results": results}
    except Exception as e:
        # Fallback to browser search
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}")
        return {"success": True, "results": [], "message": f"Search fallback launched in browser: {e}"}


def fetch_webpage_summary(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    """
    Extracts readable text content from a web page.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [Truncated: {len(text) - max_chars} characters remaining]"

        return {
            "success": True,
            "url": url,
            "title": soup.title.string.strip() if soup.title else "Untitled",
            "content": text
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch content from {url}: {str(e)}"}
