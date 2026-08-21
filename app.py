import os
import json
import time
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from search_engine import perform_serp_search, synthesize_direct_answer, check_serpapi_key
from llm_provider import (
    fetch_groq_models,
    stream_llm_response,
    generate_llm_response,
    DEFAULT_SYSTEM_PROMPT,
    SEARCH_SYNTHESIS_SYSTEM_PROMPT
)

# Load environment variables
load_dotenv()

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="NexusAI - Groq Powered Intelligent Chatbot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling & Aesthetics (Dark Glassmorphic & Modern Theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0b0f19 0%, #111827 60%, #0d1322 100%);
    }
    
    /* Header Gradient Banner */
    .header-box {
        background: linear-gradient(135deg, rgba(249, 115, 22, 0.12) 0%, rgba(59, 130, 246, 0.12) 50%, rgba(147, 51, 234, 0.12) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 20px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
    }
    
    .header-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #f97316 0%, #60a5fa 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding-bottom: 4px;
        letter-spacing: -0.5px;
    }
    
    .header-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }
    
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: rgba(249, 115, 22, 0.15);
        color: #fb923c;
        border: 1px solid rgba(249, 115, 22, 0.3);
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-top: 6px;
    }

    /* Glassmorphism Source Cards */
    .source-card {
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
        transition: all 0.2s ease-in-out;
    }
    
    .source-card:hover {
        background: rgba(51, 65, 85, 0.75);
        border-color: rgba(96, 165, 250, 0.4);
        transform: translateY(-2px);
    }
    
    .source-badge {
        display: inline-block;
        background: #2563eb;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 9999px;
        margin-right: 6px;
    }
    
    .source-domain {
        color: #38bdf8;
        font-size: 0.78rem;
        font-weight: 500;
    }
    
    .source-title {
        color: #f1f5f9;
        font-size: 0.92rem;
        font-weight: 600;
        text-decoration: none;
        display: block;
        margin-top: 4px;
    }
    
    .source-snippet {
        color: #94a3b8;
        font-size: 0.82rem;
        margin-top: 4px;
        line-height: 1.4;
    }
    
    /* Quick prompt button styling */
    .stButton>button {
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    /* Status Badge */
    .status-badge-ok {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .status-badge-err {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Persona Presets
PERSONAS = {
    "🤖 General Assistant": "You are a helpful, intelligent, and friendly AI assistant powered by Groq.",
    "💻 Expert Coder & Architect": "You are an expert full-stack software engineer and system architect. Provide clean, well-commented, robust code with explanations.",
    "⚡ Ultra-Concise & Direct": "You provide extremely fast, direct, bullet-pointed, and highly concise answers without filler words.",
    "📊 Data & Science Analyst": "You are a senior data scientist and technical researcher. Emphasize analytical rigor, statistics, and clear structured synthesis.",
    "✍️ Creative Writer & Strategist": "You are a creative writer and marketing strategist with an engaging, articulate, and compelling voice."
}

# --- Sidebar: Configuration & Settings ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8649/8649622.png", width=44)
    st.title("Settings & Engine")
    
    # 1. Engine / Provider Mode
    st.markdown("### ⚡ AI Provider")
    llm_provider = st.selectbox(
        "Inference Engine",
        ["Groq", "OpenAI", "Gemini", "OpenRouter", "Ollama (Local)", "Custom OpenAI-Compatible"],
        index=0
    )
    
    groq_api_key = ""
    llm_api_key = ""
    llm_model = ""
    custom_endpoint = ""
    
    if llm_provider == "Groq":
        default_groq = os.getenv("GROQ_API_KEY", "")
        groq_api_key = st.text_input(
            "Groq API Key",
            value=default_groq,
            type="password",
            help="Your Groq API key for ultra-fast LPU inference."
        )
        llm_api_key = groq_api_key
        
        if groq_api_key:
            groq_models = fetch_groq_models(groq_api_key)
            llm_model = st.selectbox("Groq Model", groq_models, index=0)
            st.markdown("""
            <div class="status-badge-ok">
                ⚡ Groq LPU Connected
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-badge-err">
                ● Missing Groq Key
            </div>
            """, unsafe_allow_html=True)
            
    elif llm_provider == "OpenAI":
        default_openai = os.getenv("OPENAI_API_KEY", "")
        llm_api_key = st.text_input("OpenAI API Key", value=default_openai, type="password")
        llm_model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
    elif llm_provider == "Gemini":
        default_gemini = os.getenv("GEMINI_API_KEY", "")
        llm_api_key = st.text_input("Gemini API Key", value=default_gemini, type="password")
        llm_model = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"])
    elif llm_provider == "OpenRouter":
        llm_api_key = st.text_input("OpenRouter API Key", type="password")
        llm_model = st.text_input("Model ID", value="meta-llama/llama-3.3-70b-instruct")
    elif llm_provider == "Ollama (Local)":
        custom_endpoint = st.text_input("Ollama Base URL", value="http://localhost:11434/v1/chat/completions")
        llm_model = st.text_input("Model Name", value="llama3.2")
    elif llm_provider == "Custom OpenAI-Compatible":
        custom_endpoint = st.text_input("API Base URL", value="http://localhost:8000/v1/chat/completions")
        llm_api_key = st.text_input("API Key (optional)", type="password")
        llm_model = st.text_input("Model Name", value="default")

    st.markdown("---")

    # 2. Chat Mode: Direct Chat vs Web-Grounded Search
    st.markdown("### 🌐 Search Grounding Mode")
    chat_mode = st.radio(
        "Chat Mode",
        ["💬 Direct Groq AI Chat", "🌐 Web-Grounded AI Search"],
        index=0,
        help="Direct mode gives instant conversational responses. Web-Grounded mode queries Google via SerpApi and synthesizes live sources."
    )
    
    serpapi_key = os.getenv("SERPAPI_API_KEY", "")
    search_engine_type = "google"
    country_code = "us"
    lang_code = "en"
    num_results = 6
    safe_search = "active"
    
    if chat_mode == "🌐 Web-Grounded AI Search":
        serpapi_key = st.text_input(
            "SerpApi Key (Google Grounding)",
            value=serpapi_key,
            type="password",
            help="SerpApi key for fetching real-time Google search results."
        )
        if serpapi_key:
            key_info = check_serpapi_key(serpapi_key)
            if key_info.get("valid"):
                st.markdown(f"""
                <div class="status-badge-ok">
                    ● SerpApi Active ({key_info.get('plan')})
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="status-badge-err">
                    ● {key_info.get('error', 'Invalid Key')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Please provide a SerpApi key for live web search.")
            
        search_engine_type = st.selectbox(
            "Search Type",
            ["google", "google_news", "google_scholar"],
            format_func=lambda x: {
                "google": "🌐 Google Web",
                "google_news": "📰 Google News",
                "google_scholar": "🎓 Google Scholar"
            }.get(x, x)
        )
        col_geo1, col_geo2 = st.columns(2)
        with col_geo1:
            country_code = st.selectbox("Region", ["us", "uk", "in", "ca", "au", "de", "fr", "jp"], index=0)
        with col_geo2:
            lang_code = st.selectbox("Language", ["en", "es", "fr", "de", "hi", "ja"], index=0)
        num_results = st.slider("Source Depth", min_value=3, max_value=12, value=6)

    st.markdown("---")

    # 3. Model Parameters & Persona
    st.markdown("### 🎛️ AI Persona & Parameters")
    selected_persona_name = st.selectbox("AI Persona", list(PERSONAS.keys()), index=0)
    system_prompt = PERSONAS[selected_persona_name]
    
    with st.expander("⚙️ Advanced Parameters", expanded=False):
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.05)
        max_tokens = st.slider("Max Tokens", min_value=256, max_value=4096, value=2048, step=128)
        custom_system_prompt = st.text_area("Custom System Prompt", value=system_prompt, height=80)
        if custom_system_prompt.strip():
            system_prompt = custom_system_prompt

    st.markdown("---")

    # 4. Session Controls
    st.markdown("### 🛠️ Actions & Export")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
    with col_c2:
        chat_md = f"# NexusAI Chat Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        for m in st.session_state.messages:
            chat_md += f"### {m['role'].capitalize()}\n{m['content']}\n\n"
        st.download_button(
            "📥 Export",
            data=chat_md,
            file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )

# --- Header Banner ---
st.markdown(f"""
<div class="header-box">
    <h1 class="header-title">⚡ NexusAI Streamlit Chatbot</h1>
    <p class="header-subtitle">Ultra-fast conversational AI powered by <strong>Groq LPU</strong> & optional real-time <strong>Google Web Grounding</strong>.</p>
    <div style="margin-top: 8px;">
        <span class="badge-pill">⚡ Engine: {llm_provider} ({llm_model or 'Default'})</span>
        <span class="badge-pill" style="margin-left: 8px;">{'🌐 Live Web Grounding' if chat_mode == '🌐 Web-Grounded AI Search' else '💬 Instant AI Chat'}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Quick Starter Prompt Chips (when chat is empty) ---
if not st.session_state.messages:
    st.markdown("##### 💡 Suggested Questions to Get Started")
    col1, col2, col3, col4 = st.columns(4)
    
    if chat_mode == "🌐 Web-Grounded AI Search":
        starter_prompts = [
            "🔬 Latest breakthroughs in Quantum Computing",
            "📱 Top tech news and launches today",
            "📈 Current trends in Artificial Intelligence 2026",
            "🚀 NASA latest space mission updates"
        ]
    else:
        starter_prompts = [
            "🐍 Write a Python async web scraper with error handling",
            "💡 Explain Quantum Computing in simple terms with analogies",
            "⚡ What makes Groq LPU architecture so fast for LLMs?",
            "📊 Design a clean REST API architecture for a SaaS app"
        ]
    
    if col1.button(starter_prompts[0], use_container_width=True):
        st.session_state.pending_prompt = starter_prompts[0]
        st.rerun()
    if col2.button(starter_prompts[1], use_container_width=True):
        st.session_state.pending_prompt = starter_prompts[1]
        st.rerun()
    if col3.button(starter_prompts[2], use_container_width=True):
        st.session_state.pending_prompt = starter_prompts[2]
        st.rerun()
    if col4.button(starter_prompts[3], use_container_width=True):
        st.session_state.pending_prompt = starter_prompts[3]
        st.rerun()

# --- Render Chat History ---
for msg_idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "⚡"):
        st.markdown(message["content"])
        
        # If assistant has associated search sources, display them in an expander
        if message["role"] == "assistant" and message.get("search_data"):
            sd = message["search_data"]
            sources = sd.get("sources", [])
            related_questions = sd.get("related_questions", [])
            
            if sources:
                with st.expander(f"📚 View {len(sources)} Verified Web Sources & Citations", expanded=False):
                    for src in sources:
                        idx = src.get("index", 1)
                        title = src.get("title", "Reference")
                        link = src.get("link", "#")
                        domain = src.get("domain", "")
                        snippet = src.get("snippet", "")
                        
                        st.markdown(f"""
                        <div class="source-card">
                            <div>
                                <span class="source-badge">[{idx}]</span>
                                <span class="source-domain">{domain}</span>
                            </div>
                            <a class="source-title" href="{link}" target="_blank">{title} ↗</a>
                            <div class="source-snippet">{snippet}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Show Related Questions chips
            if related_questions:
                st.markdown("##### 💡 Related Inquiries:")
                rq_cols = st.columns(min(len(related_questions), 3))
                for q_idx, rq in enumerate(related_questions[:3]):
                    with rq_cols[q_idx]:
                        if st.button(f"🔍 {rq['question']}", key=f"rq_{msg_idx}_{q_idx}", use_container_width=True):
                            st.session_state.pending_prompt = rq["question"]
                            st.rerun()

# --- Handle User Input ---
user_query = st.chat_input("Ask anything or type a prompt...")

# Check if a starter prompt was clicked
if st.session_state.pending_prompt:
    user_query = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_query:
    # 1. Append & render User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_query)
        
    # 2. Assistant Response Processing
    with st.chat_message("assistant", avatar="⚡"):
        search_data = None
        
        # Check if API Key is configured
        if not llm_api_key and llm_provider not in ["Ollama (Local)"]:
            err_msg = f"⚠️ **API Key Required**: Please provide your {llm_provider} API Key in the sidebar or `.env` file."
            st.error(err_msg)
            st.session_state.messages.append({"role": "assistant", "content": err_msg})
        else:
            # Mode A: Web Grounded Search
            if chat_mode == "🌐 Web-Grounded AI Search":
                if not serpapi_key:
                    st.warning("⚠️ **SerpApi Key Missing**: Web search grounding requires a SerpApi key. Falling back to direct AI chat.")
                    response_placeholder = st.empty()
                    with st.spinner("⚡ Groq AI is generating answer..."):
                        stream_gen = stream_llm_response(
                            provider=llm_provider,
                            api_key=llm_api_key,
                            model=llm_model,
                            query=user_query,
                            chat_history=st.session_state.messages[:-1],
                            system_prompt=system_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            base_url=custom_endpoint
                        )
                        full_res = response_placeholder.write_stream(stream_gen)
                else:
                    with st.status(f"🔍 Searching live web for: '{user_query}'...", expanded=True) as status_box:
                        st.write("🌐 Querying Google Search Engine via SerpApi...")
                        search_data = perform_serp_search(
                            query=user_query,
                            api_key=serpapi_key,
                            engine=search_engine_type,
                            num_results=num_results,
                            country=country_code,
                            language=lang_code,
                            safe_search=safe_search
                        )
                        
                        if "error" in search_data:
                            status_box.update(label="❌ Web Search Error", state="error", expanded=False)
                            st.error(search_data["error"])
                        else:
                            src_count = len(search_data.get("sources", []))
                            st.write(f"✅ Found {src_count} relevant web sources.")
                            st.write(f"🧠 Synthesizing verified answer with {llm_provider} ({llm_model})...")
                            status_box.update(label="✨ Search Grounding & Synthesis Complete", state="complete", expanded=False)
                    
                    # Stream synthesized answer
                    response_placeholder = st.empty()
                    stream_gen = stream_llm_response(
                        provider=llm_provider,
                        api_key=llm_api_key,
                        model=llm_model,
                        query=user_query,
                        search_data=search_data,
                        chat_history=st.session_state.messages[:-1],
                        system_prompt=SEARCH_SYNTHESIS_SYSTEM_PROMPT,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        base_url=custom_endpoint
                    )
                    full_res = response_placeholder.write_stream(stream_gen)
                    
                    # Render Sources expander
                    if search_data and search_data.get("sources"):
                        sources = search_data["sources"]
                        with st.expander(f"📚 View {len(sources)} Verified Web Sources & Citations", expanded=False):
                            for src in sources:
                                idx = src.get("index", 1)
                                title = src.get("title", "Reference")
                                link = src.get("link", "#")
                                domain = src.get("domain", "")
                                snippet = src.get("snippet", "")
                                st.markdown(f"""
                                <div class="source-card">
                                    <div>
                                        <span class="source-badge">[{idx}]</span>
                                        <span class="source-domain">{domain}</span>
                                    </div>
                                    <a class="source-title" href="{link}" target="_blank">{title} ↗</a>
                                    <div class="source-snippet">{snippet}</div>
                                </div>
                                """, unsafe_allow_html=True)
            
            # Mode B: Direct Fast AI Chat
            else:
                response_placeholder = st.empty()
                stream_gen = stream_llm_response(
                    provider=llm_provider,
                    api_key=llm_api_key,
                    model=llm_model,
                    query=user_query,
                    chat_history=st.session_state.messages[:-1],
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    base_url=custom_endpoint
                )
                full_res = response_placeholder.write_stream(stream_gen)
            
            # Store in chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_res,
                "search_data": search_data
            })
