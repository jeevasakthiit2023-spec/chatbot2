# ⚡ NexusSearch AI - Live Web-Grounded Streamlit Chatbot

A modern, fast, and feature-rich AI Search & Conversational Chatbot powered by **SerpApi** (real-time Google Search, Knowledge Graph, and AI Overview).

---

## 🌟 Key Features

- **🌐 Live Web Grounding**: Real-time Google Search, Google News, and Google Scholar results via SerpApi.
- **📌 Knowledge Panels & Direct Answers**: Instant extraction of Google Knowledge Graph, Answer Box snippets, and AI Overviews.
- **📚 Interactive Source Drawers**: Clickable source cards with domain badges, snippets, and direct links.
- **💡 "People Also Ask" Suggestions**: Interactive follow-up question chips to dive deeper with a single click.
- **🧠 Multi-Mode AI Synthesis**:
  - **Direct SerpApi Engine**: Works immediately with your SerpApi key.
  - **Hybrid LLM Mode (Optional)**: Connect to Groq, OpenAI, Google Gemini, Ollama (Local), or OpenRouter for Perplexity-style synthesized answers with bracketed citations `[1]`, `[2]`.
- **🎨 Glassmorphic Dark UI**: Custom modern CSS styling, animated status badges, and responsive layout.
- **📥 Chat Export**: Export conversation history to Markdown with one click.

---

## 🚀 Getting Started

### 1. Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Your SerpApi key is saved in `.env`:

```env
SERPAPI_API_KEY=c638a5a2f7c95712fe612718b914e7eb08772426b72d44b1b8cff3f7c8f26437
```

*(Optional: You can also add your `GROQ_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY` for hybrid LLM synthesis.)*

### 3. Run the App

Run using `python -m streamlit`:

```bash
python -m streamlit run app.py
```

Or double-click `run.bat` on Windows.

---

## ⚙️ Configuration Options in UI

- **Search Parameters**: Choose between Google Web, Google News, or Google Scholar.
- **Region & Language**: Filter search results by target country (e.g. `US`, `UK`, `IN`) and interface language.
- **Result Depth**: Adjust the number of search sources retrieved (3 to 15).
- **SafeSearch**: Toggle SafeSearch on/off.
