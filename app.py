import os
import json
import time
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from search_engine import perform_serp_search, synthesize_direct_answer, check_serpapi_key
from llm_provider import generate_llm_response

# Load environment variables
load_dotenv()

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="NexusSearch AI - Live Web Chatbot",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling & Aesthetics (Dark Glassmorphic & Modern Theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background & Container styling */
    .main {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0d1322 100%);
    }
    
    /* Header Gradient Banner */
    .header-box {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.15), rgba(147, 51, 234, 0.15));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    .header-title {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding-bottom: 6px;
    }
    
    .header-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }
    
    /* Glassmorphism Source Cards */
    .source-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
        transition: all 0.2s ease-in-out;
    }
    
    .source-card:hover {
        background: rgba(51, 65, 85, 0.8);
        border-color: rgba(96, 165, 250, 0.4);
        transform: translateY(-2px);
    }
    
    .source-badge {
        display: inline-block;
        background: #2563eb;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 600;
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

if "last_search_data" not in st.session_state:
    st.session_state.last_search_data = None

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# --- Sidebar: Configuration & Settings ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8649/8649622.png", width=48)
    st.title("Settings & Engine")
    
    # 1. SerpApi Key Configuration
    st.markdown("### 🔑 SerpApi Key")
    default_serp_key = os.getenv("SERPAPI_API_KEY", "")
    serpapi_key = st.text_input(
        "SerpApi API Key",
        value=default_serp_key,
        type="password",
        help="Your SerpApi key for real-time Google search grounding."
    )
    
    # Check Key status
    if serpapi_key:
        key_info = check_serpapi_key(serpapi_key)
        if key_info.get("valid"):
            st.markdown(f"""
            <div class="status-badge-ok">
                ● Connected ({key_info.get('plan')})
            </div>
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">
                Account: {key_info.get('email')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="status-badge-err">
                ● {key_info.get('error', 'Invalid Key')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Please enter your SerpApi key.")

    st.markdown("---")
    
    # 2. Search Configuration
    st.markdown("### 🔍 Search Parameters")
    search_engine_type = st.selectbox(
        "Search Engine",
        ["google", "google_news", "google_scholar"],
        format_func=lambda x: {
            "google": "🌐 Google Web Search",
            "google_news": "📰 Google News",
            "google_scholar": "🎓 Google Scholar"
        }.get(x, x)
    )
    
    col_geo1, col_geo2 = st.columns(2)
    with col_geo1:
        country_code = st.selectbox(
            "Region (gl)",
            ["us", "uk", "in", "ca", "au", "de", "fr", "jp", "br"],
            index=0,
            help="Country search results bias"
        )
    with col_geo2:
        lang_code = st.selectbox(
            "Language (hl)",
            ["en", "es", "fr", "de", "hi", "ja", "zh-cn"],
            index=0,
            help="Search results interface language"
        )
        
    num_results = st.slider("Result Depth", min_value=3, max_value=15, value=8)
    safe_search = st.selectbox("SafeSearch", ["active", "off"], index=0)

    st.markdown("---")

    # 3. AI Synthesis Mode & Optional LLM Provider
    st.markdown("### 🧠 AI Synthesis Mode")
    synthesis_mode = st.radio(
        "Synthesis Engine",
        ["Direct SerpApi Engine", "Hybrid LLM + Search"],
        help="Direct mode uses SerpApi's Knowledge Graph & AI Overview. Hybrid mode synthesizes using an LLM."
    )
    
    llm_provider = "Groq"
    llm_model = ""
    llm_api_key = ""
    custom_endpoint = ""
    
    if synthesis_mode == "Hybrid LLM + Search":
        llm_provider = st.selectbox(
            "LLM Provider",
            ["Groq", "OpenAI", "Gemini", "OpenRouter", "Ollama (Local)", "Custom OpenAI-Compatible"]
        )
        
        if llm_provider == "Groq":
            default_groq = os.getenv("GROQ_API_KEY", "")
            llm_api_key = st.text_input("Groq API Key", value=default_groq, type="password", help="Get free fast keys at console.groq.com")
            llm_model = st.selectbox("Model", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"])
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
    
    # 4. Chat Controls
    st.markdown("### 🛠️ Actions & Export")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_search_data = None
            st.rerun()
            
    with col_c2:
        # Export chat as Markdown
        chat_md = "# NexusSearch Chatbot Export\n\n"
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
st.markdown("""
<div class="header-box">
    <h1 class="header-title">⚡ NexusSearch AI</h1>
    <p class="header-subtitle">Real-time Web Grounding & Intelligent Search Agent powered by SerpApi & Live Google Search</p>
</div>
""", unsafe_allow_html=True)

# --- Quick Starter Prompt Chips (if chat is empty) ---
if not st.session_state.messages:
    st.markdown("##### 🚀 Suggested Questions")
    col1, col2, col3, col4 = st.columns(4)
    
    starter_prompts = [
        "🔬 Latest breakthroughs in Quantum Computing",
        "📱 Top tech news and launches today",
        "📈 Current trends in Artificial Intelligence 2026",
        "🚀 NASA latest space mission updates"
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
        
        # If assistant has associated search sources, display them in an expandable drawer
        if message["role"] == "assistant" and "search_data" in message and message["search_data"]:
            sd = message["search_data"]
            sources = sd.get("sources", [])
            related_questions = sd.get("related_questions", [])
            related_searches = sd.get("related_searches", [])
            
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
                st.markdown("##### 💡 People Also Ask:")
                rq_cols = st.columns(min(len(related_questions), 3))
                for q_idx, rq in enumerate(related_questions[:3]):
                    with rq_cols[q_idx]:
                        if st.button(f"🔍 {rq['question']}", key=f"rq_{msg_idx}_{q_idx}", use_container_width=True):
                            st.session_state.pending_prompt = rq["question"]
                            st.rerun()

# --- Handle User Input ---
user_query = st.chat_input("Ask anything or search live web information...")

# Check if a starter prompt was clicked
if st.session_state.pending_prompt:
    user_query = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_query:
    # 1. Display and record User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_query)
        
    # 2. Assistant Response Processing
    with st.chat_message("assistant", avatar="⚡"):
        if not serpapi_key:
            err_text = "⚠️ **SerpApi Key Missing**: Please provide your SerpApi key in the sidebar or `.env` file to enable search."
            st.error(err_text)
            st.session_state.messages.append({"role": "assistant", "content": err_text})
        else:
            with st.status(f"🔍 Searching live web for: '{user_query}'...", expanded=True) as status_box:
                st.write("🌐 Querying SerpApi Google Engine...")
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
                    status_box.update(label="❌ Search Failed", state="error", expanded=False)
                    final_response = f"⚠️ **Search Error**: {search_data['error']}"
                else:
                    sources_count = len(search_data.get("sources", []))
                    st.write(f"✅ Retrieved {sources_count} sources and knowledge panels.")
                    
                    if synthesis_mode == "Hybrid LLM + Search" and (llm_api_key or llm_provider == "Ollama (Local)"):
                        st.write(f"🧠 Synthesizing with {llm_provider} ({llm_model})...")
                        status_box.update(label="✨ Web Search & AI Synthesis Complete", state="complete", expanded=False)
                        
                        try:
                            final_response = generate_llm_response(
                                provider=llm_provider,
                                api_key=llm_api_key,
                                model=llm_model,
                                query=user_query,
                                search_data=search_data,
                                chat_history=st.session_state.messages[:-1],
                                base_url=custom_endpoint
                            )
                        except Exception as e:
                            final_response = f"⚠️ LLM Synthesis failed: {str(e)}\n\n" + synthesize_direct_answer(search_data)
                    else:
                        st.write("📝 Formatting direct knowledge & search findings...")
                        status_box.update(label="✨ Search Grounding Complete", state="complete", expanded=False)
                        final_response = synthesize_direct_answer(search_data)
            
            # Render the response
            st.markdown(final_response)
            
            # Render sources preview
            sources = search_data.get("sources", [])
            related_questions = search_data.get("related_questions", [])
            
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
                        
            if related_questions:
                st.markdown("##### 💡 People Also Ask:")
                rq_cols = st.columns(min(len(related_questions), 3))
                for q_idx, rq in enumerate(related_questions[:3]):
                    with rq_cols[q_idx]:
                        if st.button(f"🔍 {rq['question']}", key=f"rq_new_{q_idx}", use_container_width=True):
                            st.session_state.pending_prompt = rq["question"]
                            st.rerun()

            # Record Assistant Message
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response,
                "search_data": search_data
            })
            st.session_state.last_search_data = search_data
