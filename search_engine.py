"""
SerpApi Web Search & Knowledge Extraction Engine
Handles Google Web, Google News, and Scholar search queries via SerpApi.
Extracts Knowledge Graph, Answer Box, AI Overview, Organic Results, and Related Questions.
"""

import requests
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SERPAPI_BASE_URL = "https://serpapi.com/search.json"


def check_serpapi_key(api_key: str) -> Dict[str, Any]:
    """Validates the SerpApi key and returns account status."""
    if not api_key:
        return {"valid": False, "error": "API key is empty"}
    try:
        resp = requests.get(f"https://serpapi.com/account?api_key={api_key.strip()}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "valid": True,
                "email": data.get("account_email", "N/A"),
                "searches_per_month": data.get("searches_per_month", 0),
                "plan": data.get("plan_name", "Free/Standard"),
                "total_searches_left": data.get("total_searches_left", "N/A")
            }
        else:
            return {"valid": False, "error": f"Invalid key (Status {resp.status_code})"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def perform_serp_search(
    query: str,
    api_key: str,
    engine: str = "google",
    num_results: int = 8,
    country: str = "us",
    language: str = "en",
    safe_search: str = "active"
) -> Dict[str, Any]:
    """
    Executes a search on SerpApi and normalizes the results.
    """
    if not api_key:
        return {"error": "Missing SerpApi API Key. Please provide one in the sidebar or .env file."}
    
    params = {
        "q": query.strip(),
        "api_key": api_key.strip(),
        "engine": engine,
        "hl": language,
        "gl": country,
        "safe": safe_search,
    }
    
    if engine == "google":
        params["num"] = num_results
    elif engine == "google_news":
        params["gl"] = country
        params["hl"] = language
    
    try:
        response = requests.get(SERPAPI_BASE_URL, params=params, timeout=18)
        if response.status_code != 200:
            err_msg = response.json().get("error", f"HTTP {response.status_code}") if response.text else f"HTTP {response.status_code}"
            return {"error": f"SerpApi Error: {err_msg}"}
        
        raw_data = response.json()
        return parse_serp_response(raw_data, query)
    except requests.exceptions.Timeout:
        return {"error": "Search request timed out. Please try again."}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


def parse_serp_response(data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Parses SerpApi raw JSON response into structured search context."""
    result: Dict[str, Any] = {
        "query": query,
        "direct_answer": None,
        "ai_overview": None,
        "knowledge_graph": None,
        "organic_results": [],
        "news_results": [],
        "related_questions": [],
        "related_searches": [],
        "sources": []
    }
    
    # 1. Direct Answer / Answer Box / Calculation / Weather
    if "answer_box" in data:
        ab = data["answer_box"]
        ans_text = ab.get("answer") or ab.get("snippet") or ab.get("result")
        if not ans_text and "snippet_highlighted_words" in ab:
            ans_text = " ".join(ab["snippet_highlighted_words"])
        
        result["direct_answer"] = {
            "type": ab.get("type", "Answer Box"),
            "title": ab.get("title", ""),
            "answer": ans_text or str(ab),
            "link": ab.get("link", "")
        }
    
    # 2. Google AI Overview (if returned)
    if "ai_overview" in data:
        aio = data["ai_overview"]
        text_blocks = []
        if isinstance(aio, dict):
            if "text_blocks" in aio:
                for block in aio["text_blocks"]:
                    if isinstance(block, dict) and "snippet" in block:
                        text_blocks.append(block["snippet"])
                    elif isinstance(block, str):
                        text_blocks.append(block)
            elif "snippet" in aio:
                text_blocks.append(aio["snippet"])
        elif isinstance(aio, str):
            text_blocks.append(aio)
        
        if text_blocks:
            result["ai_overview"] = "\n\n".join(text_blocks)
            
    # 3. Knowledge Graph
    if "knowledge_graph" in data:
        kg = data["knowledge_graph"]
        kg_attrs = {}
        for k, v in kg.items():
            if k not in ["title", "type", "description", "source", "thumbnail", "header_images"] and isinstance(v, (str, int, float)):
                clean_key = k.replace("_", " ").title()
                kg_attrs[clean_key] = v
                
        result["knowledge_graph"] = {
            "title": kg.get("title", ""),
            "type": kg.get("type", ""),
            "description": kg.get("description", ""),
            "website": kg.get("website", ""),
            "source": kg.get("source", {}).get("name", "") if isinstance(kg.get("source"), dict) else "",
            "source_link": kg.get("source", {}).get("link", "") if isinstance(kg.get("source"), dict) else "",
            "attributes": kg_attrs
        }
    
    # 4. Organic Results
    sources_collected = []
    if "organic_results" in data:
        for idx, item in enumerate(data["organic_results"]):
            title = item.get("title", "Untitled")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            domain = ""
            if link:
                try:
                    domain = urlparse(link).netloc.replace("www.", "")
                except Exception:
                    domain = link
            
            entry = {
                "index": idx + 1,
                "title": title,
                "link": link,
                "domain": domain,
                "snippet": snippet,
                "date": item.get("date", ""),
                "sitelinks": [s.get("title") for s in item.get("sitelinks", {}).get("inline", []) if s.get("title")]
            }
            result["organic_results"].append(entry)
            
            if link and link not in [s["link"] for s in sources_collected]:
                sources_collected.append({
                    "index": len(sources_collected) + 1,
                    "title": title,
                    "link": link,
                    "domain": domain,
                    "snippet": snippet
                })

    # 5. News Results (if news engine or inline news)
    news_items = data.get("news_results", [])
    for idx, item in enumerate(news_items[:6]):
        title = item.get("title", "")
        link = item.get("link", "")
        source = item.get("source", "")
        date = item.get("date", "")
        snippet = item.get("snippet", "")
        result["news_results"].append({
            "title": title,
            "link": link,
            "source": source,
            "date": date,
            "snippet": snippet
        })
        if link and link not in [s["link"] for s in sources_collected]:
            sources_collected.append({
                "index": len(sources_collected) + 1,
                "title": title,
                "link": link,
                "domain": source or urlparse(link).netloc.replace("www.", ""),
                "snippet": snippet
            })
            
    # 6. Related Questions (People Also Ask)
    if "related_questions" in data:
        for q in data["related_questions"][:5]:
            result["related_questions"].append({
                "question": q.get("question", ""),
                "snippet": q.get("snippet", ""),
                "title": q.get("title", ""),
                "link": q.get("link", "")
            })
            
    # 7. Related Searches
    if "related_searches" in data:
        for r in data["related_searches"][:6]:
            query_str = r.get("query") or r.get("title")
            if query_str:
                result["related_searches"].append(query_str)
                
    result["sources"] = sources_collected[:10]
    return result


def synthesize_direct_answer(search_data: Dict[str, Any]) -> str:
    """
    Synthesizes a clean, structured, and informative Markdown response directly
    from SerpApi search findings (Direct Answer, Knowledge Graph, Organic, AI Overview).
    """
    if "error" in search_data:
        return f"⚠️ **Search Error**: {search_data['error']}"
    
    parts = []
    
    # 1. Direct Answer Highlight
    da = search_data.get("direct_answer")
    if da and da.get("answer"):
        parts.append(f"> 💡 **Direct Answer**: {da['answer']}")
        if da.get("link"):
            parts.append(f"*(Source: [{da.get('title', 'Reference')}]({da['link']}))*\n")

    # 2. Knowledge Graph Summary
    kg = search_data.get("knowledge_graph")
    if kg and kg.get("title"):
        kg_desc = kg.get("description", "")
        kg_type = f" *({kg['type']})*" if kg.get("type") else ""
        parts.append(f"### 📌 {kg['title']}{kg_type}")
        if kg_desc:
            parts.append(f"{kg_desc}")
        
        # Attributes if available
        if kg.get("attributes"):
            attrs_md = []
            for k, v in kg["attributes"].items():
                attrs_md.append(f"- **{k}**: {v}")
            if attrs_md:
                parts.append("\n" + "\n".join(attrs_md[:6]))
        parts.append("")

    # 3. Google AI Overview (if available)
    aio = search_data.get("ai_overview")
    if aio:
        parts.append("### 🤖 Google AI Overview")
        parts.append(f"{aio}\n")

    # 4. Synthesized Key Findings from Organic Results
    organics = search_data.get("organic_results", [])
    news = search_data.get("news_results", [])
    
    if organics or news:
        parts.append("### 🔍 Search Highlights & Findings")
        
        if organics:
            for item in organics[:5]:
                idx = item["index"]
                title = item["title"]
                snippet = item["snippet"]
                link = item["link"]
                domain = item["domain"]
                
                if snippet:
                    parts.append(f"- **[{title}]({link})** `{domain}`\n  {snippet} [[{idx}]]({link})")
                else:
                    parts.append(f"- **[{title}]({link})** `{domain}` [[{idx}]]({link})")
        
        if news:
            parts.append("\n#### 📰 Latest News Updates")
            for item in news[:3]:
                title = item["title"]
                link = item["link"]
                source = item["source"]
                date = f" *({item['date']})*" if item["date"] else ""
                parts.append(f"- [{title}]({link}) — **{source}**{date}")

    # 5. Fallback if empty
    if not parts:
        parts.append("No direct information found for this query. Try refining your search terms.")

    return "\n\n".join(parts)
