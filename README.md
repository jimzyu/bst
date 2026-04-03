# 📖 Bible Study Tool

A Streamlit application for interactive Bible study using Google Gemini AI. Generates observation, interpretation, and application questions calibrated to the reader's chosen emphasis, with threshold scenarios for group discussion facilitation. Supports Traditional Chinese, Simplified Chinese, and English.

## ✨ Features

### 📖 Emphasis Study Mode (default)
The app's primary mode. Enter a passage reference and choose how you want to engage with it today:

- **🔍 探索 Explore** — Open observation questions; notice what you notice
- **💡 理解 Understand** — Deeper interpretation questions; ask why
- **❤️ 應用 Apply** — Personal application questions; let the passage question you

Questions are generated in parallel for all three emphases upfront, so selection is instant. Each question set covers Observation, Interpretation, and Application with sub-questions calibrated to passage length.

### 🧠 Deep Study Mode (checkbox)
Runs three parallel theological analyses before generating question sets — standard theology, historical/cultural context, and application focus. Produces a richer passage summary and more precise questions for theologically complex passages.

### 📋 Passage Summary
A collapsible reference panel on the selection screen showing:
- **主題名稱** — Theme title
- **神學意義說明** — Theological significance
- **歷史背景補充** — Historical context
- **經文的診斷** — Passage diagnosis (the specific human condition the passage addresses)

Available in Traditional Chinese, Simplified Chinese, and English tabs.

### 💡 Case Study Generator (facilitator tool)
On-demand threshold scenario generation for group discussion. The app first maps the passage's distinct teaching points (one per major pericope), then generates a scenario informed by each teaching point's specific diagnosis. Facilitators select which teaching point to focus on for their session.

Features:
- Bilingual teaching point labels (Chinese + English)
- Regenerate button for fresh scenarios on the same teaching point
- Switch to a different teaching point without re-mapping

### ✍️ Interactive Quiz
Answer questions one section at a time (Observation → Interpretation → Application) and receive AI-powered feedback. Previous answers are preserved when switching between emphases within a session.

### 📊 Google Sheets Logging
Emphasis study sessions are logged automatically when the user selects an emphasis. Quiz answers and feedback are logged per question. All entries are inserted at row 2 so the newest results appear at the top.

---

## 🏗️ Architecture

```
study.py              Main application — UI flow and state management
config.py             Configuration, secrets, and constants
prompts.py            All prompt templates (emphasis, summary, mapping, scenario, evaluation)
parsers.py            Response parsing and content rendering
api_client.py         Gemini API client, parallel generation, Google Sheets logger
session_manager.py    Streamlit session state management
bible_api.py          Optional Bible text API integration
```

### Key design decisions

**Parallel generation:** All three emphasis question sets and the passage summary are generated in 4 concurrent API calls. Deep Study mode runs 3 theological drafts first, then generates 4 more in parallel — 7 calls total, but faster than sequential.

**Teaching point mapping:** Before generating a case study scenario, the app maps the passage's distinct teaching points using a structured prompt. Each teaching point has a verse range, teaching statement (bilingual), and specific diagnosis. Scenarios are then generated using `get_threshold_with_diagnosis_prompt`, which prepends the diagnosis to the scenario instruction so the model generates a scenario that embodies the passage's specific diagnostic claim rather than a generic action-gap situation.

**Answer persistence:** Quiz answers are stored per-emphasis in session state so returning to a previously answered emphasis shows the previous answers pre-filled. Persistent stores are cleared when starting a new passage.

**Threshold scenarios:** Scenarios follow four principles — rationale defensibility, show don't diagnose, end when shown, and setting variety. Each scenario has a Chinese and English version, with discussion questions designed to be genuinely arguable (Q1, either/or framing) and personally anchored (Q2, open but specific).

---

## 📦 Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd ai-tools
pip install -r requirements.txt
```

### 2. Configure secrets

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
SANDBOX_PASSWORD = "your-password"   # optional, for sandbox mode

# Optional: Google Sheets logging
GOOGLE_SHEETS_ID = "your-spreadsheet-id"

[google_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "..."
client_email = "..."
# ... other service account fields
```

### 3. Run locally

```bash
streamlit run study.py
```

---

## 🛠️ Local Tools

### test_threshold.py
Standalone script for generating threshold scenarios without the Streamlit UI. Useful for producing batches of scenarios for evaluation before using them in group sessions.

```bash
# Default: map teaching points, generate one scenario per point
python test_threshold.py --reference "雅各書1:19-27" --output results.txt

# Single scenario with diagnosis (no mapping)
python test_threshold.py --reference "雅各書2:14-17" --no-map

# Original behaviour (no mapping, no diagnosis)
python test_threshold.py --reference "雅各書2:14-17" --no-map --no-diagnosis --count 3
```

Requires `GEMINI_API_KEY` environment variable:
```bash
export GEMINI_API_KEY="your-key"   # Mac/Linux
set GEMINI_API_KEY=your-key        # Windows
```

---

## 📐 Prompt Architecture

All prompt templates live in `prompts.py` as class attributes of `PromptTemplates`:

| Template | Purpose |
|----------|---------|
| `EMPHASIS_EXPLORE/UNDERSTAND/APPLY` | Question generation for each emphasis |
| `SUMMARY_TEMPLATE` | Standalone passage summary (standard mode) |
| `SUMMARY_FROM_DRAFTS_TEMPLATE` | Richer summary drawn from three theological drafts (deep mode) |
| `PASSAGE_MAPPING_TEMPLATE` | Maps passage to distinct teaching points with diagnoses |
| `THRESHOLD_SCENARIO_INSTRUCTION` | Core scenario generation instruction with four principles |
| `THRESHOLD_WITH_THEOLOGY_TEMPLATE` | Scenario generation informed by theological drafts |
| `BASE_STUDY_TEMPLATE` | Wraps scenario instruction for API call |
| `SYSTEM_INSTRUCTION` | System-level instruction for all Gemini calls |

---

## 📋 Google Sheets Column Structure

20 columns (A–T):

| Col | Field |
|-----|-------|
| A | Timestamp |
| B | Reference |
| C | Mode (`emphasis_explore`, `emphasis_understand`, `emphasis_apply`) |
| D-F | Drafts (Deep Study only) |
| G | Question set (Final Result) |
| H, J, L | User answers (Observation, Interpretation, Application) |
| I, K, M | Feedback (Observation, Interpretation, Application) |
| N, O, P | Scores (0–10) |
| Q, R, S | Evaluation confidence (%) |
| T | Understanding confidence (%) |
