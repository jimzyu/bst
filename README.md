# 📖 聖經研讀工具 Bible Study Tool

A Streamlit application for interactive Bible study, developed for the **SAGOS Institute of Preaching & Bible Exposition**. Uses AI to generate Socratic questions calibrated to the reader's chosen emphasis, guide the reader through observation, interpretation, and application, and produce threshold scenarios for group discussion. Supports Traditional Chinese, Simplified Chinese, and English.

---

## ✨ Features

### 📖 Emphasis Selection

Enter a passage reference and choose how you want to engage with it today:

| Emphasis | Chinese | English |
|---|---|---|
| 🔍 探索 Explore | 讀讀看，留意你所看見的 | Read and notice what stands out |
| 💡 理解 Understand | 挖深一點，問為什麼 | Dig deeper, ask why |
| ❤️ 應用 Apply | 讓經文來問你 | Let the passage question you |

All three question sets and a Quick Summary are generated in parallel (4 concurrent API calls) when the user submits a reference. Emphasis selection is instant.

### 🔒 Progressive Disclosure Gate

Summary and scenario features are locked until the user completes at least one full question set (all three questions answered). This ensures engagement with the text before accessing the model's interpretation.

- **Personal study:** complete one question set to unlock
- **備課模式 Facilitator Mode toggle:** appears below the gate notice; unlocks everything immediately for session preparation
- Resets to locked on every new study session

### 📋 Passage Summary

A Quick Summary is generated alongside the questions. After completing questions, the user can request a **Deep Summary** which:

1. Runs a dedicated historical/lexical enrichment call (original language terms, cultural context, canonical connections)
2. Consolidates with the Quick Summary to produce a richer result — explicitly building on rather than replacing it

The expander title changes from **📚 經文摘要 Passage Summary** to **📚 深度經文摘要 Deep Summary** when the richer version is available.

Each summary contains four fields:
- **主題名稱** — Theme title
- **神學意義說明** — Theological significance
- **歷史背景補充** — Historical context (specific lexical, cultural, and canonical details)
- **經文的診斷** — Passage diagnosis (the specific human condition the passage addresses, named precisely enough that a reader recognises it in themselves)

Available in Traditional Chinese, Simplified Chinese, and English tabs.

### ✍️ Socratic Question Loop

Answer questions one type at a time (Observation → Interpretation → Application). After each answer:

- AI evaluates as **COMPLETE**, **INCOMPLETE**, or **INACCURATE**
- COMPLETE: user rates depth (表面 / 適中 / 很深) and continues
- INCOMPLETE/INACCURATE: AI generates a targeted follow-up or redirect question without revealing the answer

Previous answers are preserved when switching between emphases within a session.

### 🎯 Threshold Scenario Generator

On-demand threshold scenario generation for group discussion, available after completing questions. The app:

1. Maps the passage's distinct teaching points (verse range, bilingual teaching statement, specific diagnosis)
2. Presents the teaching points for selection
3. Generates a scenario informed by the selected teaching point's diagnosis

Scenarios follow four principles: rationale defensibility, show-don't-diagnose, end at the threshold moment, and setting variety. Each scenario includes two discussion questions — Q1 (genuinely arguable either/or) and Q2 (personally anchored, specific to the protagonist's situation).

Scenario quality scales with available context in session state:
- **Deep Summary generated:** historical draft provides richer rationalisation vocabulary and cultural specificity
- **Quick Summary only:** summary text used as lighter enrichment
- **Neither:** teaching point diagnosis only (original behaviour)

### 📊 Session Assessment

At session completion:
- **Per-question depth rating:** 表面 / 適中 / 很深 (recorded to Sheets col U)
- **Session self-assessment:** 和上週一樣 / 注意到了一些東西 / 有些驚訝 / 不確定 (recorded to Sheets col V)

---

## 🏗️ Architecture

```
study.py              Main application — UI flow, state management, SAGOS CSS
config.py             Configuration, model selection, secrets
prompts.py            All prompt templates and generation methods
parsers.py            Response parsing and content rendering
api_client.py         API client (Gemini/Anthropic/Gloo), parallel generation, Sheets logger
session_manager.py    Streamlit session state management
bible_api.py          Optional Bible text API integration
name_generator.py     Protagonist name generation for scenarios
```

### Key design principles

**Misreading identification preamble:** Before generating OIA questions, the model identifies 2–3 most likely misreadings of the passage from its rhetorical structure — what assumption is each verse arguing against? Questions are then calibrated against these misreadings. Embedded invisibly in all three emphasis templates via `MISREADING_PREAMBLE`. Produces measurably sharper questions than generic OIA prompting (Haiku 4.5 Standard: 9/10 vs 7.5/10 pre-preamble).

**System override principle:** Gemini Flash models treat the system instruction as a hard output template, overriding user-turn format instructions. Any call whose required output format differs from `SYSTEM_INSTRUCTION` passes a `system_override` parameter to `generate_content()` or `generate_content_quality()`. Currently applied to: `map_passage_teaching_points` (neutral mapping override) and all scenario generation calls (`SCENARIO_SYSTEM` constant).

**Progressive disclosure:** The tool withholds summary and scenario content until the user has completed at least one question set. This implements the generation effect — producing answers before seeing the model's interpretation produces more durable learning. Facilitator Mode bypasses this gate.

**Parallel generation:** All three emphasis question sets and the Quick Summary are generated in 4 concurrent API calls at startup. Deep Summary uses 2 sequential calls on demand (historical enrichment → consolidation).

**Teaching point mapping:** Before scenario generation, the app maps the passage's distinct teaching points using a structured prompt with a neutral system override. Scenarios are generated via `get_threshold_with_diagnosis_prompt`, which prepends the diagnosis to the scenario instruction so the model generates a scenario that embodies the passage's specific diagnostic claim.

**Answer persistence:** Quiz answers are stored per-emphasis in session state. Returning to a previously answered emphasis shows previous answers pre-filled. All stores reset on new passage.

---

## ⚙️ Configuration

Model selection is controlled by three flags in `config.py`:

```python
USE_GLOO = False        # Use Gloo AI Studio wrapper
USE_ANTHROPIC = False   # Use Anthropic Claude directly
# Both False = direct Gemini API (recommended)
```

**Recommended configurations (based on 18-scenario evaluation series):**

| Config | Fast model | Quality model | Notes |
|---|---|---|---|
| **Recommended** | Gemini 2.5 Flash (direct) | Gemini 2.5 Flash (direct) | Best scenario quality; fastest |
| **Alternative** | Haiku 4.5 (direct) | Haiku 4.5 (direct) | Best question quality (9/10); most stable |
| **Quality runs** | Haiku 4.5 (direct) | Sonnet 4.6 (direct) | Most original scenario structures |
| Avoid | Any Gloo-wrapped | Any Gloo-wrapped | Quality floor degraded vs direct API |

- Temperature: `0.3`
- Max retries: `4` with exponential backoff (3s → 6s → 12s → 24s)
- Anthropic SDK internal retries disabled (`max_retries=0`) — tenacity controls all retry behaviour
- Max output tokens: `8192` (Anthropic path)

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
# Choose ONE API configuration:

# Option 1: Direct Gemini (recommended)
GEMINI_API_KEY = "your-gemini-api-key"

# Option 2: Direct Anthropic
ANTHROPIC_API_KEY = "your-anthropic-api-key"

# Option 3: Gloo (experimentation only)
GLOO_CLIENT_ID = "your-gloo-client-id"
GLOO_CLIENT_SECRET = "your-gloo-client-secret"

# Optional
SANDBOX_PASSWORD = "your-password"
BIBLE_API_KEY = "your-youversion-app-key"

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

## 📐 Prompt Architecture

All templates are class attributes of `PromptTemplates` in `prompts.py`:

| Template | Purpose |
|---|---|
| `SYSTEM_INSTRUCTION` | System-level instruction; defines study-guide output format and validation rules |
| `MISREADING_PREAMBLE` | Pre-question rhetorical reasoning step; embedded in all emphasis templates |
| `EMPHASIS_EXPLORE/UNDERSTAND/APPLY` | OIA question generation with misreading preamble (STEP 1/STEP 2) |
| `SUMMARY_TEMPLATE` | Quick Summary — single fast-model call |
| `SUMMARY_ENRICHED_TEMPLATE` | Deep Summary — builds on Quick Summary + historical enrichment draft |
| `SUMMARY_FROM_DRAFTS_TEMPLATE` | Legacy three-draft consolidation (retained for compatibility) |
| `PASSAGE_MAPPING_TEMPLATE` | Maps passage to distinct teaching points with diagnoses |
| `THRESHOLD_SCENARIO_INSTRUCTION` | Core scenario generation; format requirements at 29–30% to prevent attention dropout in smaller models |
| `EVALUATION_TEMPLATE` | Per-answer evaluation with COMPLETE/INCOMPLETE/INACCURATE flags; calibrated per emphasis level |
| `FOLLOWUP_QUESTION_TEMPLATE` | Socratic follow-up for incomplete answers |
| `REDIRECT_QUESTION_TEMPLATE` | Redirect question for inaccurate answers |
| `BASE_STUDY_TEMPLATE` | Base wrapper for scenario and deep study calls |

---

## 📊 Google Sheets Column Structure

22 columns (A–V):

| Col | Field | Notes |
|---|---|---|
| A | Timestamp | |
| B | Reference | |
| C | Mode | `emphasis_explore`, `emphasis_understand`, `emphasis_apply` |
| D | Draft 1 (Standard) | Legacy — not populated in current flow |
| E | Draft 2 (Historical) | Legacy — not populated in current flow |
| F | Draft 3 (Application) | Legacy — not populated in current flow |
| G | Final Result / AI Answer Key | Full question set text |
| H | User Answer — Observation | |
| I | Feedback — Observation | |
| J | User Answer — Interpretation | |
| K | Feedback — Interpretation | |
| L | User Answer — Application | |
| M | Feedback — Application | |
| N | Score — Observation | 0–10 |
| O | Score — Interpretation | 0–10 |
| P | Score — Application | 0–10 |
| Q | Confidence — Observation (%) | AI evaluation confidence |
| R | Confidence — Interpretation (%) | |
| S | Confidence — Application (%) | |
| T | AI Understanding Confidence (%) | Overall passage understanding |
| U | Question Depth Ratings | 表面/適中/很深 per question |
| V | Session Self-Assessment | End-of-session self-rating |

All entries inserted at row 2 — newest results appear at the top.

---

## 🛠️ Local Tools

### test_threshold.py

Standalone script for generating threshold scenarios without the Streamlit UI. Useful for producing evaluation batches before group sessions.

```bash
# Map teaching points, generate one scenario per point
python test_threshold.py --reference "雅各書1:19-27" --output results.txt

# Single scenario with diagnosis (no mapping)
python test_threshold.py --reference "雅各書2:14-17" --no-map

# Original behaviour (no mapping, no diagnosis)
python test_threshold.py --reference "雅各書2:14-17" --no-map --no-diagnosis --count 3
```

Requires `GEMINI_API_KEY` environment variable.

---

## 🎨 UI Design

The tool uses the **SAGOS brand colour system** injected via CSS at app initialisation:

| Role | Colour | Usage |
|---|---|---|
| Forest green | `#2D7A2D` / `#1A5C1A` | Primary brand, active states, Explore cards |
| Warm brown | `#7A4520` | Secondary accent, Understand cards, secondary buttons |
| Berry purple | `#7B3B8B` | Apply cards |
| Warm white | `#F9F8F5` | Page background |

Typography: **Lora** (serif, headers) + **Noto Sans TC** (Chinese body text).

Responsive breakpoints: ≤800px (iPad portrait — tighter padding), ≤640px (phone — single-column cards).

---

## 📈 API Call Budget

A typical full session makes approximately **11–16 API calls**:

| Step | Action | Calls | Model tier |
|---|---|---|---|
| Start Study | Questions (×3) + Quick Summary | 4 parallel | Fast |
| Answer questions | Evaluate (×3) + follow-ups (0–3) | 3–6 | Quality |
| Deep Summary | Historical draft + consolidation | 2 sequential | Quality |
| Scenario | Teaching point mapping + generate | 2 | Fast + Quality |
| Additional scenarios | Per extra teaching point | 0–2 | Quality |

At Haiku 4.5 pricing, a typical 14-call session costs approximately $0.03–0.05.
