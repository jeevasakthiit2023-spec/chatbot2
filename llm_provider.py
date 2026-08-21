"""
Multi-Provider LLM Integration for Streamlit AI Chatbot with Groq Support.
Supports: Groq (ultra-fast inference), OpenAI, Google Gemini, Anthropic, OpenRouter, and Ollama.
Supports both direct conversational chat & live web search context synthesis.
"""

import os
import json
import requests
from typing import Dict, Any, List, Generator, Optional


DEFAULT_SYSTEM_PROMPT = """You are a highly intelligent, helpful, and friendly AI Assistant powered by Groq's high-speed inference engine.
Your responses should be:
- Accurate, well-reasoned, and clear
- Nicely structured using Markdown (headers, bullet points, code blocks)
- Engaging, professional, and directly addressing the user's inquiry.
"""

SEARCH_SYNTHESIS_SYSTEM_PROMPT = """You are a smart, accurate AI Search Assistant powered by real-time web search.
You have access to live Google search results for the user's inquiry.
Your goals:
1. Synthesize a comprehensive, clear, well-structured, and factual answer based on the provided search results.
2. Cite your sources using numbered brackets like [1], [2], [3] that match the provided source indexes.
3. Use clean Markdown formatting with headers, bullet points, and bold text for readability.
4. If there are conflicting or recent updates, highlight the most up-to-date information.
5. Keep a conversational, helpful, and concise tone.
"""


def fetch_groq_models(api_key: str) -> List[str]:
    """
    Fetches the available chat-capable models from Groq API.
    Falls back to a standard curated list if unreachable.
    """
    fallback_models = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound",
        "groq/compound-mini",
        "qwen/qwen3.6-27b",
        "allam-2-7b",
        "canopylabs/orpheus-v1-english"
    ]
    if not api_key:
        return fallback_models
    
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            models = [
                m["id"] for m in data.get("data", [])
                if not any(ex in m["id"] for ex in ["whisper", "guard", "embedding", "moderation"])
            ]
            # Prioritize standard high-performing models
            top_priority = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound", "qwen/qwen3.6-27b"]
            sorted_models = [m for m in top_priority if m in models] + [m for m in models if m not in top_priority]
            return sorted_models if sorted_models else fallback_models
    except Exception:
        pass
    return fallback_models


def format_search_context(search_data: Optional[Dict[str, Any]]) -> str:
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


def build_messages(
    query: str,
    search_data: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """Constructs the message payload for chat completions."""
    if search_data and not search_data.get("error"):
        sys = system_prompt or SEARCH_SYNTHESIS_SYSTEM_PROMPT
        search_context = format_search_context(search_data)
        user_prompt = f"""User Question: {query}

--- LIVE WEB SEARCH CONTEXT ---
{search_context}
--- END SEARCH CONTEXT ---

Please provide an accurate, up-to-date answer referencing the citations [1], [2], etc."""
    else:
        sys = system_prompt or DEFAULT_SYSTEM_PROMPT
        user_prompt = query

    messages = [{"role": "system", "content": sys}]
    
    # Add recent history (up to last 8 messages)
    if chat_history:
        for msg in chat_history[-8:]:
            if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
                
    messages.append({"role": "user", "content": user_prompt})
    return messages


def stream_llm_response(
    provider: str,
    api_key: str,
    model: str,
    query: str,
    search_data: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    base_url: Optional[str] = None
) -> Generator[str, None, None]:
    """
    Streams response tokens from the selected LLM provider.
    """
    messages = build_messages(query, search_data, chat_history, system_prompt)
    
    if provider == "Groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        yield from _stream_openai_compatible(url, api_key, model or "openai/gpt-oss-120b", messages, temperature, max_tokens)
    elif provider == "OpenAI":
        url = "https://api.openai.com/v1/chat/completions"
        yield from _stream_openai_compatible(url, api_key, model or "gpt-4o-mini", messages, temperature, max_tokens)
    elif provider == "OpenRouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        yield from _stream_openai_compatible(url, api_key, model or "meta-llama/llama-3.3-70b-instruct", messages, temperature, max_tokens)
    elif provider == "Ollama (Local)":
        url = base_url or "http://localhost:11434/v1/chat/completions"
        yield from _stream_openai_compatible(url, "ollama", model or "llama3.2", messages, temperature, max_tokens)
    elif provider == "Custom OpenAI-Compatible":
        url = base_url or "http://localhost:8000/v1/chat/completions"
        yield from _stream_openai_compatible(url, api_key or "sk-dummy", model or "default", messages, temperature, max_tokens)
    elif provider == "Gemini":
        full_res = _call_gemini_api(api_key, model or "gemini-1.5-flash", query, messages)
        yield full_res
    else:
        yield f"⚠️ Unsupported provider: {provider}"


def generate_llm_response(
    provider: str,
    api_key: str,
    model: str,
    query: str,
    search_data: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    base_url: Optional[str] = None
) -> str:
    """
    Non-streaming response generator from the selected LLM provider.
    """
    chunks = []
    for chunk in stream_llm_response(
        provider=provider,
        api_key=api_key,
        model=model,
        query=query,
        search_data=search_data,
        chat_history=chat_history,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        base_url=base_url
    ):
        chunks.append(chunk)
    return "".join(chunks)


def _stream_openai_compatible(
    url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Generator[str, None, None]:
    """Handles SSE stream from OpenAI/Groq compatible chat APIs."""
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        if resp.status_code != 200:
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text or f"HTTP {resp.status_code}"
            yield f"⚠️ **API Error ({resp.status_code})**: {err_msg}"
            return

        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data_str = decoded[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                except Exception:
                    continue
    except requests.exceptions.Timeout:
        yield "⚠️ Request timed out. Please try again."
    except Exception as e:
        yield f"⚠️ Request failed: {str(e)}"


def _call_gemini_api(api_key: str, model: str, prompt: str, messages: List[Dict[str, str]]) -> str:
    """Calls Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
    headers = {"Content-Type": "application/json"}
    
    contents = []
    for m in messages:
        role = "user" if m["role"] in ["user", "system"] else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
        
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
