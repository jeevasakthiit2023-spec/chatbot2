# ⚡ NexusAI - Groq Powered Streamlit Chatbot

A high-performance, modern AI Chatbot powered by **Groq's Ultra-Fast LPU Inference** with optional real-time **Google Web Grounding via SerpApi**.

---

## 🌟 Key Features

- **⚡ Ultra-Fast Groq Inference**: Real-time streaming responses with Groq's high-speed LPU engine (hundreds of tokens/sec).
- **🤖 Dynamic Model Discovery**: Auto-discovers and supports models including `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `groq/compound`, `qwen/qwen3.6-27b`, and more.
- **💬 Dual Chat Modes**:
  - **⚡ Direct Groq AI Chat**: Instant conversational AI with persona selection (Coder, Assistant, Analyst, Writer), streaming tokens, and multi-turn context memory.
  - **🌐 Web-Grounded AI Search**: Queries live Google Search results (via SerpApi) and synthesizes answers with citations `[1]`, `[2]`, interactive source cards, and "People Also Ask" chips.
- **🎛️ AI Persona & Parameter Controls**: Custom system prompts, temperature sliders, token limits, and role templates.
- **🎨 Glassmorphic Dark UI**: Modern sleek theme with custom CSS styling, glowing badges, and responsive design.
- **📥 Chat Export**: Export conversation transcripts to Markdown with a single click.

---

## 🚀 Getting Started

### 1. Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Configure your keys in `.env` (refer to `.env.example`):

```env
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_API_KEY=your_serpapi_api_key_here
```

### 3. Run the App

Run using `streamlit`:

```bash
python -m streamlit run app.py
```

Or double-click `run.bat` on Windows.
