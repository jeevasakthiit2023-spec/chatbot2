"""
Multi-Provider LLM Integration for Web Search Synthesis.
Supports: Groq, OpenAI, Google Gemini, Anthropic, Ollama, and OpenRouter.
Feeds live SerpApi web search context to the LLM for Perplexity-style cited answers.
"""

import os
import json
import requests
from typing import Dict, Any, List, Generator, Optional


SYSTEM_PROMPT = """You are a smart, accurate AI Search Assistant powered by real-time web search.
You have access to live Google search results for the user's inquiry.
Your goals:
1. Synthesize a comprehensive, clear, well-structured, and factual answer based on the provided search results.
2. Cite your sources using numbered brackets like [1], [2], [3] that match the provided source indexes.
3. Use clean Markdown formatting with headers, bullet points, and bold text for readability.
4. If there are conflicting or recent updates, highlight the most up-to-date information.
5. Keep a conversational, helpful, and concise tone.
"""


def format_search_context(search_data: Dict[str, Any]) -> str:
    """Formats search results into a clean prompt context for the LLM."""
    if not search_data or "error" in search_data:
        return "No external search context available."
    
    context_lines = []
    
    # Direct Answer
    if search_data.get("direct_answer"):
        da = search_data["direct_answer"]
        context_lines.append(f"Google Direct Answer: {da.get('answer', '')}")
        
    # Knowledge Graph
    if search_data.get("knowledge_graph"):
        kg = search_data["knowledge_graph"]
        context_lines.append(f"Knowledge Graph: {kg.get('title', '')} ({kg.get('type', '')}): {kg.get('description', '')}")
        if kg.get("attributes"):
            for k, v in kg["attributes"].items():
                context_lines.append(f"- {k}: {v}")
                
    # Google AI Overview
    if search_data.get("ai_overview"):
        context_lines.append(f"Google AI Overview:\n{search_data['ai_overview']}")
        
    # Organic Sources
    context_lines.append("\nWeb Search Results:")
    for s in search_data.get("sources", []):
        idx = s.get("index", 1)
        title = s.get("title", "")
        snippet = s.get("snippet", "")
        domain = s.get("domain", "")
        context_lines.append(f"[{idx}] {title} ({domain}):\nSnippet: {snippet}")
        
    return "\n".join(context_lines)


def generate_llm_response(
    provider: str,
    api_key: str,
    model: str,
    query: str,
    search_data: Dict[str, Any],
    chat_history: List[Dict[str, str]] = None,
    base_url: Optional[str] = None
) -> str:
    """
    Calls the specified LLM provider with search context.
    """
    search_context = format_search_context(search_data)
    
    prompt = f"""User Question: {query}

--- LIVE WEB SEARCH CONTEXT ---
{search_context}
--- END SEARCH CONTEXT ---

Please provide an accurate, up-to-date answer referencing the citations [1], [2], etc."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add recent chat history (last 4 messages)
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": prompt})
    
    # Provider routing
    if provider == "Groq":
        return _call_openai_compatible(
            url="https://api.groq.com/openai/v1/chat/completions",
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
            messages=messages
        )
    elif provider == "OpenAI":
        return _call_openai_compatible(
            url="https://api.openai.com/v1/chat/completions",
            api_key=api_key,
            model=model or "gpt-4o-mini",
            messages=messages
        )
    elif provider == "OpenRouter":
        return _call_openai_compatible(
            url="https://openrouter.ai/api/v1/chat/completions",
            api_key=api_key,
            model=model or "meta-llama/llama-3.3-70b-instruct",
            messages=messages
        )
    elif provider == "Ollama (Local)":
        endpoint = base_url or "http://localhost:11434/v1/chat/completions"
        return _call_openai_compatible(
            url=endpoint,
            api_key="ollama",
            model=model or "llama3.2",
            messages=messages
        )
    elif provider == "Gemini":
        return _call_gemini_api(api_key, model or "gemini-1.5-flash", prompt, messages)
    elif provider == "Custom OpenAI-Compatible":
        endpoint = base_url or "http://localhost:8000/v1/chat/completions"
        return _call_openai_compatible(
            url=endpoint,
            api_key=api_key or "sk-dummy",
            model=model or "default",
            messages=messages
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _call_openai_compatible(url: str, api_key: str, model: str, messages: List[Dict[str, str]]) -> str:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 1500
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            err = resp.json().get("error", {}).get("message", resp.text) if resp.text else f"Status {resp.status_code}"
            return f"⚠️ LLM Error ({resp.status_code}): {err}"
        
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ LLM Request Failed: {str(e)}"


def _call_gemini_api(api_key: str, model: str, prompt: str, messages: List[Dict[str, str]]) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
    headers = {"Content-Type": "application/json"}
    
    # Format contents
    contents = [{"parts": [{"text": SYSTEM_PROMPT + "\n\n" + prompt}]}]
    payload = {"contents": contents}
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return f"⚠️ Gemini API Error ({resp.status_code}): {resp.text}"
        
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]
        return "⚠️ Received empty response from Gemini."
    except Exception as e:
        return f"⚠️ Gemini Request Failed: {str(e)}"
