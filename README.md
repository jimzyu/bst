# 📖 聖經研讀工具 Bible Study Tool (BST)

A Streamlit application for structured Bible study — the AI generates calibrated questions at three depth levels, evaluates answers, and produces threshold scenarios for group discussion. Supports Traditional Chinese, Simplified Chinese, and English.

---

## How it works

Enter a passage reference and choose an emphasis level. Three question sets and a summary are generated in parallel. Work through the questions; the AI evaluates each answer and generates follow-up questions if needed. After completing a set, a passage summary and scenario generator become available.

---

## Bible Tools project context

| Tool | Purpose |
|---|---|
| **System A** | AI-generated exegetical analysis of biblical chapters using the 10-step framework — the knowledge base |
| **BST** — Bible Study Tool | Structured question sets, evaluation, and scenarios. Trains exegetical discipline. |
| **BLT** — Bible Learning Tool | Socratic conversation. Trains interpretive instinct and personal formation. |
| **BPT** — Bible Preaching Tool | *(Future)* Trains the craft of communicating a passage to a specific audience. |

---

## Features

**Emphasis selection** — choose how to engage with the passage today:

| Emphasis | Focus |
|---|---|
| 🔍 探索 Explore | Read and notice what stands out |
| 💡 理解 Understand | Dig deeper, ask why |
| ❤️ 應用 Apply | Let the passage question you |

**Guided question loop** — answer observation, interpretation, and application questions one at a time. The AI evaluates each answer as complete, incomplete, or inaccurate, and generates targeted follow-up questions when needed.

**Passage summary** — a Quick Summary is available after completing questions. A richer Deep Summary (with original language terms, cultural context, and canonical connections) can be requested on demand.

**Threshold scenario generator** — generates a realistic scenario for group discussion, anchored to a specific teaching point from the passage. Each scenario ends at a threshold moment with two discussion questions.

**Facilitator mode** — bypasses the progressive disclosure gate for session preparation.

---

## Setup

```bash
git clone <repo-url>
cd bst
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key"   # Option 1: Direct Gemini (default)
# ANTHROPIC_API_KEY = "..."   # Option 2: Direct Anthropic
# SANDBOX_MODE = true         # Optional: password gate
# SANDBOX_PASSWORD = "..."
```

```bash
streamlit run study.py
```

---

## Files

```
study.py              Main application — UI flow, state management
config.py             Configuration, model selection, secrets
prompts.py            All prompt templates and generation methods
parsers.py            Response parsing and content rendering
api_client.py         AI client (Gemini / Anthropic / Gloo), parallel generation
session_manager.py    Streamlit session state management
name_generator.py     Protagonist name generation for scenarios
```
