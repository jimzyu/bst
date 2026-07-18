"""
Bible Study Tool - Refactored Application
A Streamlit application for generating Bible study guides using Google Gemini AI.
"""
import streamlit as st
from opencc import OpenCC
import logging

# Local imports
from config import Config
from name_generator import generate_name, build_context_paragraph
from prompts import PromptTemplates
from parsers import ResponseParser, ContentRenderer, QuizParser, LessonPlanParser, QuestionBankParser, ReflectionParser
from api_client import GeminiClient, GeminiAPIError
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_sandbox_authentication():
    """
    Check if sandbox mode is enabled and authenticate user.
    Returns True if user should proceed, False if authentication fails.
    """
    # Check if sandbox mode is enabled
    sandbox_mode = Config.get_sandbox_mode()
    
    if not sandbox_mode:
        # Sandbox mode disabled, proceed normally
        return True
    
    # Initialize authentication state
    if "sandbox_authenticated" not in st.session_state:
        st.session_state.sandbox_authenticated = False
    
    # If already authenticated, proceed
    if st.session_state.sandbox_authenticated:
        return True
    
    # Show login screen
    st.title("🔒 Bible Study Tool - Sandbox Mode")
    st.info("This app is currently in testing mode. Please enter the password to continue.")
    
    password = st.text_input("Enter Password:", type="password", key="sandbox_password")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Login", type="primary"):
            if password == Config.get_sandbox_password():
                st.session_state.sandbox_authenticated = True
                st.success("✅ Authentication successful!")
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
    
    # Stop execution here - don't show the rest of the app
    return False


def initialize_app():
    """Initialize the application."""
    # Page configuration
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        page_icon=Config.PAGE_ICON,
        layout="centered"
    )
    
    # Validate API key
    Config.validate_api_key()
    
    # Initialize session state
    SessionManager.initialize()
    
    # Initialize Chinese converter
    if 'cc_converter' not in st.session_state:
        st.session_state.cc_converter = OpenCC('t2s')
    
    # Initialize API client — reinitialise if provider has changed
    provider_key = f"gloo={Config.USE_GLOO}_anthropic={Config.USE_ANTHROPIC}"
    if ('gemini_client' not in st.session_state or
            st.session_state.get('api_provider_key') != provider_key):
        api_key = Config.get_api_key()
        st.session_state.gemini_client = GeminiClient(
            api_key=api_key,
            system_instruction=PromptTemplates.SYSTEM_INSTRUCTION
        )
        st.session_state.api_provider_key = provider_key
        provider = "Gloo" if Config.USE_GLOO else "Anthropic" if Config.USE_ANTHROPIC else "Gemini"
        logger.info(f"Application initialised with {provider}")
    
    # Initialize Bible API client
    if 'bible_client' not in st.session_state:
        bible_api_key = Config.get_bible_api_key()
        if bible_api_key:
            from bible_api import BibleAPIClient
            st.session_state.bible_client = BibleAPIClient(bible_api_key)
            logger.info("Bible API client initialized")
        else:
            st.session_state.bible_client = None
            logger.warning("Bible API key not found - passage display will be disabled")

    # ── SAGOS brand CSS ───────────────────────────────────────────────────────
    st.markdown("""
<style>
/* ── SAGOS Design System ─────────────────────────────────────────────── */
:root {
    --green:       #8B1A2A;
    --green-dark:  #5C1018;
    --green-light: #F4E8EA;
    --brown:       #7A4520;
    --brown-light: #F5EDE6;
    --purple:      #7B3B8B;
    --purple-light:#F5EAF7;
    --warm-white:  #F9F8F5;
    --card-bg:     #FFFFFF;
    --text:        #1A1A1A;
    --text-muted:  #666666;
    --border:      #E0D8CF;
    --shadow:      0 2px 8px rgba(45,122,45,0.10);
    --shadow-hover:0 6px 20px rgba(45,122,45,0.18);
    --radius:      12px;
    --radius-sm:   8px;
}

/* Page background */
.stApp { background-color: var(--warm-white); }
.block-container { padding-top: 2rem !important; }

/* ── Typography ──────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Noto+Sans+TC:wght@400;500;700&display=swap');

.stApp, .stMarkdown, .stText {
    font-family: 'Noto Sans TC', 'PingFang TC', sans-serif;
    color: var(--text);
}
h1, h2, h3 { font-family: 'Lora', 'PingFang TC', serif; }

/* App title on landing screen */
.stApp h1 {
    color: var(--green-dark);
    font-size: 2.2rem !important;
    font-weight: 600;
    letter-spacing: -0.02em;
    border-bottom: 3px solid var(--green);
    padding-bottom: 0.4rem;
    margin-bottom: 0.5rem;
}
.stApp h2 { color: var(--brown); font-size: 1.1rem !important; font-weight: 400; }

/* Reference header (### on Screen 1) */
.stApp h3 {
    color: var(--green-dark);
    font-family: 'Lora', serif;
    font-size: 1.5rem !important;
    margin-bottom: 1rem;
    padding-left: 0.6rem;
    border-left: 4px solid var(--green);
}

/* ── Input ───────────────────────────────────────────────────────────── */
.stTextInput > div > div > input {
    border: 2px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--card-bg);
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    font-size: 1.05rem;
    padding: 0.6rem 0.9rem;
    transition: border-color 0.2s;
    opacity: 1 !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--green);
    box-shadow: 0 0 0 3px rgba(45,122,45,0.12);
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
}
.stTextInput > div > div > input::placeholder {
    color: #999 !important;
    -webkit-text-fill-color: #999 !important;
    opacity: 1 !important;
}

/* ── Primary button (Start Study / Done) ─────────────────────────────── */
.stButton > button[kind="primary"] {
    background: var(--green) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.55rem 1.4rem !important;
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s !important;
    box-shadow: var(--shadow) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--green-dark) !important;
    box-shadow: var(--shadow-hover) !important;
    transform: translateY(-1px) !important;
}

/* ── Secondary button (Back / Try another) ───────────────────────────── */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--brown) !important;
    border: 1.5px solid var(--brown) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    transition: background 0.2s, color 0.2s !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--brown-light) !important;
    color: var(--brown) !important;
}

/* ── Emphasis cards ──────────────────────────────────────────────────── */
/* Explore — burgundy accent */
[data-testid="column"]:nth-child(1) .stButton > button {
    background: var(--green-light) !important;
    color: var(--green-dark) !important;
    border: 2px solid var(--green) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s !important;
}
[data-testid="column"]:nth-child(1) .stButton > button:hover {
    background: var(--green) !important;
    color: #fff !important;
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-hover) !important;
}

/* Understand — brown accent */
[data-testid="column"]:nth-child(2) .stButton > button {
    background: var(--brown-light) !important;
    color: var(--brown) !important;
    border: 2px solid var(--brown) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s !important;
}
[data-testid="column"]:nth-child(2) .stButton > button:hover {
    background: var(--brown) !important;
    color: #fff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(122,69,32,0.18) !important;
}

/* Apply — purple accent */
[data-testid="column"]:nth-child(3) .stButton > button {
    background: var(--purple-light) !important;
    color: var(--purple) !important;
    border: 2px solid var(--purple) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s !important;
}
[data-testid="column"]:nth-child(3) .stButton > button:hover {
    background: var(--purple) !important;
    color: #fff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(123,59,139,0.18) !important;
}

/* ── Info / success / warning boxes ──────────────────────────────────── */
.stAlert[data-baseweb="notification"] {
    border-radius: var(--radius) !important;
}
div[data-testid="stNotificationContentInfo"] {
    background: var(--green-light) !important;
    border-left: 4px solid var(--green) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Expanders ───────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: var(--card-bg) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    color: var(--text) !important;
    transition: border-color 0.2s !important;
}
.streamlit-expanderHeader:hover {
    border-color: var(--green) !important;
    color: var(--green-dark) !important;
}

/* ── Toggle (facilitator) ────────────────────────────────────────────── */
.stToggle [data-testid="stToggle"] { accent-color: var(--green); }

/* ── Divider ─────────────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 1.2rem 0 !important; }

/* ── Spinner / status ────────────────────────────────────────────────── */
.stSpinner > div { border-top-color: var(--green) !important; }

/* ── Tabs ────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid var(--border); }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: var(--green-dark) !important;
    border-bottom: 3px solid var(--green) !important;
    font-weight: 600;
}
.stTabs [data-baseweb="tab"] { color: var(--text-muted); }

/* ── Success message ─────────────────────────────────────────────────── */
.stSuccess { border-left: 4px solid var(--green) !important; }

/* ── Caption / small text ────────────────────────────────────────────── */
.stCaption { color: var(--text-muted) !important; font-size: 0.82rem !important; }
small { color: var(--text-muted); font-size: 0.82rem; }

/* ── Card wrapper (used for question display) ────────────────────────── */
.sagos-card {
    background: var(--card-bg);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow);
}
.sagos-card-green  { border-left: 4px solid var(--green); }
.sagos-card-brown  { border-left: 4px solid var(--brown); }
.sagos-card-purple { border-left: 4px solid var(--purple); }

/* ── Question card ───────────────────────────────────────────────────── */
.question-card {
    background: var(--card-bg);
    border-left: 4px solid var(--green);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 1rem 1.3rem;
    margin-bottom: 0.8rem;
    box-shadow: var(--shadow);
    line-height: 1.9;
}
.question-card.brown  { border-left-color: var(--brown); }
.question-card.purple { border-left-color: var(--purple); }

/* ── Feedback card ───────────────────────────────────────────────────── */
.feedback-card {
    background: #F0F7F0;
    border: 1px solid var(--green);
    border-radius: var(--radius-sm);
    padding: 0.9rem 1.2rem;
    margin-top: 0.6rem;
    font-size: 0.95rem;
    line-height: 1.85;
}

/* ── Completion badge on emphasis cards ──────────────────────────────── */
.completion-badge {
    display: inline-block;
    background: var(--green);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: 6px;
    vertical-align: middle;
}

/* ── Unlock banner ───────────────────────────────────────────────────── */
.unlock-banner {
    background: linear-gradient(90deg, var(--green-light) 0%, #fff 100%);
    border: 1.5px solid var(--green);
    border-radius: var(--radius-sm);
    padding: 0.7rem 1.1rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.92rem;
    color: var(--green-dark);
    font-weight: 500;
}

/* ── Chinese body text line height ──────────────────────────────────── */
.stMarkdown p, .stText p, .stWrite { line-height: 1.85 !important; }

/* ── Responsive: iPad portrait (≤800px) — tighter cards ─────────────── */
@media (max-width: 800px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .stApp h1 { font-size: 1.7rem !important; }
    [data-testid="column"] { min-width: 140px; }
}

/* ── Responsive: phone (≤640px) — single column cards ───────────────── */
@media (max-width: 640px) {
    [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
    [data-testid="column"] { width: 100% !important; flex: none !important; }
    .block-container { padding-left: 0.7rem !important; padding-right: 0.7rem !important; }
}
</style>
""", unsafe_allow_html=True)


def render_ui():
    """Render the main UI."""
    labels = Config.LABELS

    # Branded landing header
    st.markdown("""
<div style="
    background: linear-gradient(135deg, #5C1018 0%, #8B1A2A 60%, #B03050 100%);
    border-radius: 16px;
    padding: 2rem 2.2rem 1.6rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 4px 20px rgba(45,122,45,0.20);
">
  <div style="font-family:'Lora',serif;font-size:1.9rem;font-weight:600;
              color:#FFFFFF;letter-spacing:-0.01em;margin-bottom:0.3rem;">
    📖 聖經研讀工具
  </div>
  <div style="font-size:1.05rem;color:rgba(255,255,255,0.85);font-weight:400;">
    Bible Study Tool
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown(
        f"<p style='color:#666;font-size:0.95rem;margin-bottom:1rem;'>"
        f"{labels['input_prompt']}</p>",
        unsafe_allow_html=True
    )

    # Input
    reference = st.text_input(
        labels['input_label'],
        placeholder=labels['input_placeholder']
    )

    return reference


def process_study_request(reference: str):
    """
    Process a study request.

    UPDATED 2026-07-16 — BST Consolidation Plan §4, Start Study retirement build step 5,
    option 1 (repoint, don't delete). "開始研讀 Start Study" now leads to the same
    Question Bank / single-select flow as the "📚 問題庫 Question Bank" button, rather
    than the old three-set emphasis flow — per the target architecture (§2.1: Start
    Study absorbs into Question Bank, retires as a separate pathway). The old flow
    (process_emphasis_selection, display_emphasis_interface, generate_all_emphasis_parallel)
    is deliberately left completely intact and reachable only by direct state manipulation
    — not deleted, not unlinked from the codebase — kept as a working reference for at
    least one more round, per the explicit decision not to bet deletion on one round of
    live testing. Rate-limiting, input validation, and error handling below are unchanged
    and apply the same way to the new destination.

    Args:
        reference: Bible reference input
    """
    labels = Config.LABELS
    client = st.session_state.gemini_client

    # Check rate limiting
    can_proceed, wait_time = SessionManager.can_make_request(Config.REQUEST_COOLDOWN_SECONDS)
    if not can_proceed:
        st.warning(f"請等待 {int(wait_time) + 1} 秒後再試 (Please wait {int(wait_time) + 1} seconds)")
        return

    # Validate input
    if not reference.strip():
        st.warning(labels['error_empty'])
        return

    # Record request
    SessionManager.record_request()

    try:
        st.session_state.qbank_reference = reference.strip()
        st.session_state.qbank_active = True
        st.session_state.qbank_raw_result = None
        st.rerun()

    except (GeminiAPIError, Exception) as e:
        logger.error(f"API error: {str(e)}")
        SessionManager.record_error()
        error_str = str(e)
        if '529' in error_str or 'overloaded' in error_str.lower():
            st.warning(
                "🕐 AI 服務目前負載較高，請稍候片刻再試。\n\n"
                "The AI service is temporarily overloaded — this is not a problem with "
                "your setup. Please wait 30–60 seconds and try again."
            )
        elif '429' in error_str or 'rate_limit' in error_str.lower():
            st.warning(
                "⏳ 請求過於頻繁，請稍候再試。\n\n"
                "Rate limit reached. Please wait a moment before trying again."
            )
        elif '401' in error_str or '403' in error_str or 'api_key' in error_str.lower():
            st.error(
                f"🔑 API 金鑰錯誤 (API Key Error): {error_str}\n\n"
                "Please check your API key configuration."
            )
        else:
            st.error(f"API 錯誤 (API Error): {error_str}")
            st.info("Please try again. If the problem persists, check your API key and quota.")


def process_emphasis_selection(reference: str, client):
    """
    Generate all three emphasis question sets in parallel (Standard Mode —
    misreading preamble, no theological context). The user selects instantly
    with no wait.

    UPDATED 2026-07-16 — BST Consolidation Plan §4, Start Study retirement build step 4.
    Previously also generated a passage summary in the same parallel call — removed;
    summary generation is retired from Start Study (see display_emphasis_interface's
    unlocked branch and NOTES.md "BST Consolidation Plan" for the full reasoning).
    """
    status_msg = "正在準備三種學習重點的問題組... Preparing all question sets..."

    with st.status(status_msg, expanded=True) as status:
        def cb(msg):
            status.update(label=f"生成中... {msg}")

        all_results = client.generate_all_emphasis_parallel(
            reference, status_callback=cb)

        SessionManager.start_emphasis(reference, all_results)

        status.update(label="✅ 準備完成！Ready.", state="complete", expanded=False)
    st.rerun()


def _generate_quick_summary(reference: str, client):
    """Generate a quick passage summary (single call, no theological drafts)."""
    prompt = PromptTemplates.get_summary_prompt(reference)
    return client.generate_content_quality(prompt)


def _generate_deep_summary(reference: str, client):
    """
    Generate a Deep Summary using a lean 2-call path:
      Call 1: Historical/lexical enrichment draft
      Call 2: Consolidation using Quick Summary + historical draft

    The Quick Summary (already in session state) serves as the theological
    foundation, eliminating the redundant Draft 1 and the discarded Draft 3.
    Guarantees Deep Summary is richer than Quick Summary by explicitly
    building on it. Returns the synthesised summary text, or None on failure.
    """
    try:
        # Quick Summary is already in session state from initial generation
        quick_summary = st.session_state.get('emphasis_summary', '')

        # Call 1: Historical enrichment only — the unique value of Deep Summary
        historical_prompt = PromptTemplates.BASE_STUDY_TEMPLATE.format(
            ref=reference,
            focus=PromptTemplates.FOCUS_AREAS['historical'],
            case_study_instruction=""
        )
        historical_draft = client.generate_content_quality(historical_prompt)

        # Store draft for scenario enrichment (Step 3 pipeline)
        st.session_state.emphasis_theological_drafts = [historical_draft]

        # Call 2: Consolidation — builds on Quick Summary, enriched by history
        enriched_prompt = PromptTemplates.get_summary_enriched_prompt(
            reference, quick_summary, historical_draft)
        return client.generate_content_quality(enriched_prompt)

    except Exception as e:
        logger.error(f"Deep summary generation failed: {str(e)}")
        return None



def _build_scenario_prompt(reference, diagnosis, used_names):
    """Build a scenario prompt enriched with context and a randomised protagonist name.
    Reads context directly from Streamlit widget state — no Apply button needed.

    Context enrichment priority (best available from session state):
      1. Theological drafts (from Deep Summary) — richest
      2. Quick summary text — lightweight but still useful
      3. No context — TP diagnosis only (original behaviour)
    """
    import random
    import streamlit as st
    # Read directly from dropdown widget keys
    UNSET = "（不指定）"
    region    = st.session_state.get("ctx_region", "灣區")
    profession = st.session_state.get("ctx_profession", UNSET)
    life_stage = st.session_state.get("ctx_life_stage", UNSET)
    scene      = st.session_state.get("ctx_scene", UNSET)
    context = {
        'region':     region,
        'profession': "" if profession == UNSET else profession,
        'life_stage': "" if life_stage == UNSET else life_stage,
        'scene':      "" if scene == UNSET else scene,
    }
    gender = random.choice(["male", "female"])
    name = generate_name(
        gender=gender,
        region=context['region'],
        used_names=used_names,
        scene=context['scene']
    )
    ctx_with_name = {**context, 'protagonist_name': name, 'protagonist_gender': gender}
    context_para = build_context_paragraph(ctx_with_name)

    # Build the best available passage context for scenario enrichment
    drafts = st.session_state.get('emphasis_theological_drafts')
    summary = st.session_state.get('emphasis_summary')
    if drafts:
        # Deep Summary was generated — use all three draft texts joined
        context_summary = "\n\n---\n\n".join(drafts)
    elif summary:
        # Quick Summary available — use it as lighter enrichment
        context_summary = summary
    else:
        context_summary = None

    prefix = "請以繁體中文回應以下所有內容。\n\n"
    base = PromptTemplates.get_threshold_with_diagnosis_prompt(
        reference, diagnosis, context_summary=context_summary)
    return prefix + context_para + base

def display_emphasis_interface():
    """Display the emphasis study interface — selection, question set, or quiz."""

    EMPHASIS_OPTIONS = {
        'explore': {'label': '🔍 探索 Explore', 'desc': '讀讀看，留意你所看見的', 'desc_en': 'Read and notice what stands out'},
        'understand': {'label': '💡 理解 Understand', 'desc': '挖深一點，問為什麼', 'desc_en': 'Dig deeper, ask why'},
        'apply': {'label': '❤️ 應用 Apply', 'desc': '讓經文來問你', 'desc_en': 'Let the passage question you'},
    }

    reference = st.session_state.emphasis_reference
    selected = st.session_state.emphasis_selected
    result = st.session_state.emphasis_result
    client = st.session_state.gemini_client

    st.markdown(f"### 📖 {reference}")

    # ── SCREEN 1: No emphasis selected yet ──
    if not selected or not result:
        # Completion state for badge display
        all_answers = st.session_state.get('emphasis_all_answers', {})
        required = {'observation', 'interpretation', 'application'}

        # Gate: show summary and scenario only after completing at least one
        # question set, OR when facilitator mode is active.
        unlocked = (SessionManager.has_completed_any_emphasis()
                    or st.session_state.facilitator_mode)

        def _facilitator_toggle():
            """Render the facilitator toggle — called in both locked and unlocked states."""
            tcol1, tcol2 = st.columns([4, 1])
            with tcol2:
                facilitator = st.toggle(
                    "備課模式",
                    value=st.session_state.facilitator_mode,
                    help="備課模式讓引導者在作答之前即可查看摘要和情境案例。\n"
                         "Facilitator mode unlocks summary and scenario without completing questions.",
                    key="facilitator_toggle"
                )
                if facilitator != st.session_state.facilitator_mode:
                    st.session_state.facilitator_mode = facilitator
                    st.rerun()

        # Notice above cards — precondition shown before emphasis choice
        if not unlocked:
            st.markdown(
                '<div style="'
                'background:#F5F3F0;'
                'border:1.5px solid #C8BFB5;'
                'border-left:4px solid #A89880;'
                'border-radius:var(--radius-sm);'
                'padding:0.55rem 1rem;'
                'margin-bottom:0.8rem;'
                'font-size:0.88rem;'
                'color:#555;'
                'line-height:1.5;'
                '">'
                '📝 作答完一組問題後，將可查看經文摘要與情境案例。'
                '<span style="color:#888;font-weight:400;"> · '
                'Complete one set of questions to unlock summary and scenario.</span>'
                '</div>',
                unsafe_allow_html=True
            )

        card_styles = {
            'explore':    ('var(--green)',  'var(--green-light)',  'var(--green-dark)'),
            'understand': ('var(--brown)',  'var(--brown-light)',  'var(--brown)'),
            'apply':      ('var(--purple)', 'var(--purple-light)', 'var(--purple)'),
        }
        cols = st.columns(3)
        for i, (key, opt) in enumerate(EMPHASIS_OPTIONS.items()):
            border_col, bg_col, text_col = card_styles[key]
            completed = required.issubset(all_answers.get(key, {}).keys())
            badge = '<span class="completion-badge">✓ 完成</span>' if completed else ''
            with cols[i]:
                st.markdown(f"""
<div style="
    background:{bg_col};
    border:2px solid {border_col};
    border-radius:12px;
    padding:1rem 1.1rem 0.6rem;
    margin-bottom:0.5rem;
    min-height:110px;
">
  <div style="font-size:1.05rem;font-weight:700;color:{text_col};margin-bottom:0.3rem;">
    {opt['label']}{badge}
  </div>
  <div style="font-size:0.95rem;color:#333;margin-bottom:0.2rem;">{opt['desc']}</div>
  <div style="font-size:0.78rem;color:#777;">{opt['desc_en']}</div>
</div>
""", unsafe_allow_html=True)
                if st.button(f"選擇", key=f"emphasis_{key}", use_container_width=True):
                    SessionManager.select_emphasis(key)
                    # Log selected question set to Google Sheets
                    selected_result = st.session_state.emphasis_all_results.get(key, '')
                    if selected_result and client.draft_logger:
                        try:
                            row_num = client.draft_logger.log_emphasis_study(
                                reference, key, selected_result)
                            st.session_state.emphasis_sheets_row = row_num
                            logger.info(f"Emphasis logged: {reference} / {key} -> row {row_num}")
                        except Exception as log_err:
                            logger.error(f"Emphasis logging FAILED: {log_err}", exc_info=True)
                    elif not client.draft_logger:
                        logger.warning("Emphasis logging skipped: draft_logger is None")
                    st.rerun()

        if not unlocked:
            _facilitator_toggle()
            if st.button("← 返回 Back", type="secondary"):
                SessionManager.end_emphasis()
                st.rerun()
            return
        else:
            _facilitator_toggle()
            # Added 2026-07-16 — BST Consolidation Plan §4, Start Study retirement build
            # step 4. Summary and scenario generation RETIRED from Start Study's display
            # here — both moved to become Lesson Plan / facilitator-only content, per the
            # design decision that Start Study's reward is now the personalized
            # BST_REFLECTION_TEMPLATE reflection (see display_single_question_interface),
            # not a generic passage summary. Summary content's four fields are now covered
            # by Lesson Plan's Layer 1 (經文的診斷 added there the same day to avoid losing
            # that field — see NOTES.md). Scenario/case-study generation has NO Lesson Plan
            # equivalent yet — deliberately deferred, not lost: _build_scenario_prompt()
            # and the underlying generate_case_study()/map_passage_teaching_points()
            # machinery are left completely intact and unused below, ready to be given a
            # proper home once that decision is made, rather than deleted.
            if not st.session_state.facilitator_mode:
                st.markdown(
                    '<div class="unlock-banner">'
                    '🌱 你完成了一組問題！'
                    '<span style="color:#555;font-weight:400;font-size:0.88rem;">'
                    ' Nice work completing a question set!</span>'
                    '</div>',
                    unsafe_allow_html=True
                )
            st.info(
                "📚 想看經文摘要或情境案例？這些現已整合進備課計畫中。"
                "  ·  Looking for the passage summary or discussion scenario? "
                "Those are now part of Lesson Plan."
            )

            st.markdown("---")
            if st.button("← 返回 Back", type="secondary"):
                SessionManager.end_emphasis()
                st.rerun()
            return


    opt = EMPHASIS_OPTIONS[selected]

    # ── SCREEN 2: Quiz interaction active ──
    if st.session_state.emphasis_quiz_active:
        st.markdown(f"### {opt['label']} — {opt['desc']}")
        st.markdown("---")

        # Quiz complete — show summary
        if SessionManager.is_emphasis_quiz_complete():
            st.success("🎉 完成！You've worked through all three sections.")
            type_labels = {
                "observation": "📖 觀察 Observation",
                "interpretation": "🤔 解釋 Interpretation",
                "application": "💡 應用 Application"
            }
            for qtype in ["observation", "interpretation", "application"]:
                if qtype in st.session_state.emphasis_quiz_feedbacks:
                    with st.expander(type_labels[qtype]):
                        # Original answer
                        st.markdown(f"**你的答案 Your answer:**")
                        st.write(st.session_state.emphasis_quiz_answers.get(qtype, ''))

                        # Follow-up Q&A if present
                        fu_q = st.session_state.emphasis_followup_questions.get(qtype)
                        fu_ans = st.session_state.emphasis_followup_answers.get(qtype, '')
                        if fu_q and fu_ans:
                            feedback_text_for_flag = st.session_state.emphasis_quiz_feedbacks[qtype]
                            flag_for_q, _ = QuizParser.parse_evaluation_flags(feedback_text_for_flag)
                            icon = "🔍" if flag_for_q == 'INCOMPLETE' else "📖"
                            fu_label = "跟進問題 Follow-up" if flag_for_q == 'INCOMPLETE' else "再看看經文 Look Again"
                            st.markdown(f"**{icon} {fu_label}:**")
                            ch_q, en_q = fu_q
                            st.markdown(f"_{ch_q}_")
                            st.markdown(f"**你的跟進回應 Your follow-up response:**")
                            st.write(fu_ans)

                        st.markdown("---")
                        # Evaluation (combined if follow-up was done)
                        feedback_text = st.session_state.emphasis_quiz_feedbacks[qtype]
                        ch_fb, en_fb = QuizParser.parse_evaluation_feedback(feedback_text)
                        eval_tab_label = "綜合回饋" if fu_ans else "回饋"
                        ftab1, ftab2 = st.tabs([eval_tab_label, "English Feedback"])
                        with ftab1:
                            st.markdown(ch_fb or "")
                        with ftab2:
                            st.markdown(en_fb or "")
            st.markdown("---")

            # ── Session-end self-assessment ────────────────────────────────
            assessment_options = {
                "和上週一樣": "Same as last week — nothing especially new",
                "注意到了一些東西": "Noticed something — a detail or question I hadn't seen",
                "有些驚訝": "Surprised — the passage said something I didn't expect",
                "不確定": "Not sure — still processing",
            }
            current_assessment = st.session_state.emphasis_session_assessment
            st.markdown(
                "<div style='font-size:0.95em;font-weight:600;margin-bottom:6px;'>"
                "今天讀完這段經文，你的感受是什麼？"
                "</div>"
                "<div style='font-size:0.82em;color:#888;margin-bottom:12px;'>"
                "How would you describe where you ended up with this passage today?"
                "</div>",
                unsafe_allow_html=True
            )
            if current_assessment:
                st.success(f"✓ {current_assessment}")
                st.caption(assessment_options.get(current_assessment, ""))
            else:
                acols = st.columns(2)
                option_items = list(assessment_options.items())
                for idx, (label, help_text) in enumerate(option_items):
                    with acols[idx % 2]:
                        if st.button(label, key=f"assess_{label}",
                                     help=help_text, use_container_width=True):
                            st.session_state.emphasis_session_assessment = label
                            st.rerun()

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← 換一個重點 Try another emphasis", type="secondary"):
                    st.session_state.emphasis_selected = None
                    st.session_state.emphasis_result = None
                    st.session_state.emphasis_quiz_active = False
                    st.session_state.emphasis_quiz_question = 0
                    st.session_state.emphasis_quiz_feedbacks = {}
                    st.session_state.emphasis_followup_questions = {}
                    st.session_state.emphasis_followup_answers = {}
                    st.session_state.emphasis_followup_done = {}
                    st.rerun()
            with col2:
                done_disabled = not st.session_state.emphasis_session_assessment
                if st.button("✅ 完成 Done", type="primary", disabled=done_disabled):
                    # Log ratings + assessment to Sheets before ending session
                    try:
                        sheets_row = st.session_state.get('emphasis_sheets_row')
                        if sheets_row and client.draft_logger:
                            client.draft_logger.log_session_completion(
                                row_number=sheets_row,
                                question_ratings=st.session_state.emphasis_question_ratings,
                                session_assessment=st.session_state.emphasis_session_assessment
                            )
                    except Exception as log_err:
                        logger.warning(f"Session completion logging failed: {log_err}")
                    SessionManager.end_emphasis()
                    st.rerun()
            return

        # Current question
        question_type = SessionManager.get_emphasis_question_type()
        question_text = st.session_state.emphasis_quiz_questions.get(question_type, "")
        subquestions = QuizParser.split_into_subquestions(question_text)
        total_subquestions = len(subquestions)
        current_sub_idx = st.session_state.emphasis_quiz_subquestion

        type_labels = {
            "observation": "📖 觀察 Observation",
            "interpretation": "🤔 解釋 Interpretation",
            "application": "💡 應用 Application"
        }
        type_card_class = {
            "observation": "",
            "interpretation": "brown",
            "application": "purple"
        }
        card_cls = type_card_class.get(question_type, "")
        st.markdown(
            f'<div class="question-card {card_cls}">'
            f'<div style="font-size:0.78rem;font-weight:700;letter-spacing:0.06em;'
            f'color:var(--text-muted);text-transform:uppercase;margin-bottom:0.5rem;">'
            f'{type_labels.get(question_type, question_type)}</div>'
            f'<div style="font-size:1rem;line-height:1.9;">{question_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Already evaluated this question
        if question_type in st.session_state.emphasis_quiz_feedbacks:
            feedback_text = st.session_state.emphasis_quiz_feedbacks[question_type]
            flag, note = QuizParser.parse_evaluation_flags(feedback_text)
            followup_done = st.session_state.emphasis_followup_done.get(question_type, False)
            followup_q = st.session_state.emphasis_followup_questions.get(question_type)
            needs_followup = flag in ('INCOMPLETE', 'INACCURATE') and not followup_done

            if needs_followup:
                # ── Follow-up / Redirect pending: hide evaluation, show question only ──
                if not followup_q:
                    # Generate follow-up or redirect question
                    label = "思考一個跟進問題..." if flag == 'INCOMPLETE' else "回到經文看看..."
                    with st.spinner(f"{label}"):
                        original_q = st.session_state.emphasis_quiz_questions.get(question_type, '')
                        user_ans = st.session_state.emphasis_quiz_answers.get(question_type, '')
                        if flag == 'INCOMPLETE':
                            ch_q, en_q = client.generate_followup_question(
                                reference=reference,
                                question_type=question_type,
                                emphasis=selected,
                                original_question=original_q,
                                user_answer=user_ans,
                                missing_note=note
                            )
                        else:  # INACCURATE
                            ch_q, en_q = client.generate_redirect_question(
                                reference=reference,
                                question_type=question_type,
                                emphasis=selected,
                                original_question=original_q,
                                user_answer=user_ans,
                                correction_note=note
                            )
                        st.session_state.emphasis_followup_questions[question_type] = (ch_q, en_q)
                        st.rerun()
                else:
                    icon = "🔍" if flag == 'INCOMPLETE' else "📖"
                    label = "跟進問題 Follow-up Question" if flag == 'INCOMPLETE' else "再看看經文 Look Again"
                    st.markdown(f"### {icon} {label}")
                    ch_q, en_q = followup_q
                    st.info(ch_q)
                    if en_q:
                        st.caption(en_q)
                    followup_answer = st.text_area(
                        "Your response (你的回應):",
                        height=120,
                        placeholder="Type your response here... / 在此輸入你的回應...",
                        key=f"followup_{question_type}"
                    )
                    if st.button("提交回應 Submit Response", type="primary",
                                 disabled=not followup_answer.strip()):
                        st.session_state.emphasis_followup_answers[question_type] = followup_answer
                        # Run second evaluation combining original + follow-up answer
                        with st.spinner("重新評估... Re-evaluating..."):
                            original_ans = st.session_state.emphasis_quiz_answers.get(question_type, '')
                            fu_label = "follow-up" if flag == 'INCOMPLETE' else "re-read response"
                            combined_answer = (
                                f"Initial answer: {original_ans}\n\n"
                                f"After {fu_label} question — additional response: {followup_answer}"
                            )
                            original_q = st.session_state.emphasis_quiz_questions.get(question_type, '')
                            new_feedback = client.evaluate_answer(
                                reference=reference,
                                question_type=question_type,
                                question=original_q,
                                user_answer=combined_answer,
                                ai_answer=result,
                                emphasis=selected
                            )
                            # Replace the first evaluation with the combined one
                            st.session_state.emphasis_quiz_feedbacks[question_type] = new_feedback
                            SessionManager.save_emphasis_followup_done(question_type)
                        st.rerun()

            else:
                # ── Show answers + combined evaluation ──
                st.success("✅ Answered!")
                collected = SessionManager.get_emphasis_subquestion_answers(question_type)
                for i, sq in enumerate(subquestions):
                    with st.expander(f"Sub-question {i+1}" if total_subquestions > 1 else "你的答案 Your Answer"):
                        st.markdown(f"**Q:** {sq}")
                        if i < len(collected):
                            st.write(collected[i])

                # Show follow-up Q&A if present
                fu_q = st.session_state.emphasis_followup_questions.get(question_type)
                fu_ans = st.session_state.emphasis_followup_answers.get(question_type, '')
                if fu_q and fu_ans:
                    icon = "🔍" if flag == 'INCOMPLETE' else "📖"
                    fu_label = "跟進問題 Follow-up" if flag == 'INCOMPLETE' else "再看看經文 Look Again"
                    with st.expander(f"{icon} {fu_label}"):
                        ch_q, en_q = fu_q
                        st.markdown(f"**問題:** {ch_q}")
                        if en_q:
                            st.caption(en_q)
                        st.markdown(f"**你的回應:** {fu_ans}")

                # Combined evaluation (replaces first evaluation after follow-up)
                eval_label = "💬 綜合回饋 Combined Feedback" if fu_ans else "💬 回饋 Feedback"
                with st.expander(eval_label):
                    ch_fb, en_fb = QuizParser.parse_evaluation_feedback(feedback_text)
                    ftab1, ftab2 = st.tabs(["中文", "English"])
                    with ftab1:
                        st.markdown(ch_fb or "")
                    with ftab2:
                        st.markdown(en_fb or "")

                # ── Post-answer question depth rating ──────────────────────
                existing_rating = st.session_state.emphasis_question_ratings.get(question_type)
                if existing_rating:
                    st.markdown(
                        f"<div style='color:#888;font-size:0.85em;margin-bottom:8px;'>"
                        f"你對這個問題的感受：<strong>{existing_rating}</strong></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='font-size:0.9em;margin-bottom:4px;color:#555;'>"
                        "這個問題對你來說感覺怎麼樣？"
                        "<span style='color:#888;font-size:0.8em;'> How did this question feel?</span>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                    rcol1, rcol2, rcol3 = st.columns(3)
                    rating_options = [
                        ("表面", "Surface — stayed on the text surface"),
                        ("適中", "Moderate — went a bit deeper"),
                        ("很深", "Deep — genuinely challenged me"),
                    ]
                    for col, (label, help_text) in zip([rcol1, rcol2, rcol3], rating_options):
                        with col:
                            if st.button(label, key=f"rate_{question_type}_{label}",
                                         help=help_text, use_container_width=True):
                                st.session_state.emphasis_question_ratings[question_type] = label
                                st.rerun()

                # Continue only enabled once rated
                rated = question_type in st.session_state.emphasis_question_ratings
                if st.button("Continue ➡️", type="primary", disabled=not rated):
                    SessionManager.advance_emphasis_question()
                    st.rerun()

        # Collecting answers
        elif current_sub_idx < total_subquestions:
            collected = SessionManager.get_emphasis_subquestion_answers(question_type)
            if total_subquestions > 1:
                st.markdown("**Questions for this section:**")
                for i, sq in enumerate(subquestions):
                    if i < current_sub_idx:
                        st.markdown(
                            f"<div style='padding:8px 12px;border-left:3px solid #4CAF50;margin-bottom:8px;opacity:0.75;'>"
                            f"<strong>{i+1}. {sq}</strong><br>"
                            f"<em style='color:#555;'>Your answer: {collected[i]}</em></div>",
                            unsafe_allow_html=True)
                    elif i == current_sub_idx:
                        st.markdown(
                            f"<div style='padding:8px 12px;border-left:3px solid #2196F3;background:rgba(33,150,243,0.07);margin-bottom:8px;'>"
                            f"<strong>{i+1}. {sq}</strong> ◀ <em>Answer this now</em></div>",
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f"<div style='padding:8px 12px;border-left:3px solid #ccc;margin-bottom:8px;opacity:0.5;'>"
                            f"<strong>{i+1}. {sq}</strong></div>",
                            unsafe_allow_html=True)
            else:
                # Single subquestion — already shown in the question-card above; don't repeat
                pass

            # Pre-populate with previous answer if returning to this emphasis
            prev_subq_answers = SessionManager.get_emphasis_subquestion_answers(question_type)
            prev_value = prev_subq_answers[current_sub_idx] if current_sub_idx < len(prev_subq_answers) else ""

            user_answer = st.text_area(
                "Your Answer (你的答案):",
                value=prev_value,
                height=150,
                placeholder="Type your answer here... / 在此輸入你的答案...",
                key=f"emph_answer_{question_type}_{current_sub_idx}"
            )
            is_last = (current_sub_idx == total_subquestions - 1)
            btn_label = "Submit Answer 提交答案" if is_last else "Next Sub-question ➡️"

            if st.button(btn_label, type="primary", disabled=not user_answer.strip()):
                SessionManager.save_emphasis_subquestion_answer(question_type, user_answer)
                if is_last:
                    all_answers = SessionManager.get_emphasis_subquestion_answers(question_type)
                    combined_answer = "\n\n".join(
                        f"Sub-question {i+1}: {a}" for i, a in enumerate(all_answers)
                    ) if total_subquestions > 1 else all_answers[0]
                    combined_question = "\n".join(
                        f"{i+1}. {sq}" for i, sq in enumerate(subquestions)
                    ) if total_subquestions > 1 else subquestions[0]

                    with st.spinner("Evaluating... 評估中..."):
                        feedback = client.evaluate_answer(
                            reference=reference,
                            question_type=question_type,
                            question=combined_question,
                            user_answer=combined_answer,
                            ai_answer=result,
                            emphasis=selected
                        )
                        SessionManager.save_emphasis_quiz_answer(question_type, combined_answer, feedback)
                        # Log quiz answer to Google Sheets
                        try:
                            sheets_row = st.session_state.get('emphasis_sheets_row')
                            if sheets_row:
                                client.draft_logger.log_emphasis_quiz_answer(
                                    sheets_row, question_type, combined_answer, feedback)
                        except Exception as log_err:
                            logger.warning(f"Emphasis quiz answer logging failed: {log_err}")
                    st.rerun()
                else:
                    SessionManager.advance_emphasis_subquestion()
                    st.rerun()
        return

    # ── SCREEN 3: Question set displayed — offer to answer or move on ──
    st.markdown(f"### {opt['label']} — {opt['desc']}")
    st.markdown("---")

    ch_text, en_text = ResponseParser.parse_ai_response(result)
    tab1, tab2, tab3 = st.tabs(["繁體中文", "简体中文", "English"])
    with tab1:
        ContentRenderer.render_emphasis_content(ch_text or result, Config.LABELS)
    with tab2:
        sim_text = st.session_state.cc_converter.convert(ch_text or result)
        ContentRenderer.render_emphasis_content(sim_text, Config.LABELS)
    with tab3:
        ContentRenderer.render_emphasis_content(en_text or "", Config.LABELS)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← 換一個重點 Try another emphasis", type="secondary"):
            st.session_state.emphasis_selected = None
            st.session_state.emphasis_result = None
            st.session_state.emphasis_quiz_active = False
            st.session_state.emphasis_quiz_question = 0
            st.session_state.emphasis_quiz_feedbacks = {}
            st.session_state.emphasis_followup_questions = {}
            st.session_state.emphasis_followup_answers = {}
            st.session_state.emphasis_followup_done = {}
            st.rerun()
    with col2:
        if st.button("✍️ 回答問題 Answer Questions", type="primary"):
            questions = QuizParser.extract_questions_from_study(result)
            if questions:
                SessionManager.start_emphasis_quiz(questions)
                st.rerun()
            else:
                st.warning("Could not extract questions. Please try regenerating.")
    with col3:
        if st.button("✅ 完成 Done", type="secondary"):
            SessionManager.end_emphasis()
            st.rerun()



def display_bible_passage(reference: str, location: str = "expander"):
    """
    Display Bible passage in English and Chinese.
    
    Args:
        reference: Bible reference
        location: "expander" for collapsible section, "sidebar" for sidebar display
    """
    if not st.session_state.bible_client:
        return
    
    # Fetch passage
    passages = st.session_state.bible_client.fetch_both_languages(reference)
    
    if not passages:
        logger.warning(f"Could not fetch Bible passage for: {reference}")
        return
    
    if location == "sidebar":
        # Display in sidebar (for Quiz Mode)
        with st.sidebar:
            st.markdown("### 📖 Bible Passage")
            st.markdown(f"**{reference}**")
            
            if 'chinese' in passages:
                chinese_ref, chinese_text = passages['chinese']
                with st.expander("中文 (FEB)", expanded=True):
                    st.markdown(chinese_text)
            
            if 'english' in passages:
                english_ref, english_text = passages['english']
                with st.expander("English (WEB)", expanded=False):
                    st.markdown(english_text)
    
    else:
        # Display as expander (for Study Mode)
        with st.expander("📖 View Bible Passage", expanded=False):
            tab1, tab2 = st.tabs(["中文 (FEB)", "English (WEB)"])
            
            with tab1:
                if 'chinese' in passages:
                    chinese_ref, chinese_text = passages['chinese']
                    st.markdown(f"**{chinese_ref}**")
                    st.markdown(chinese_text)
                else:
                    st.info("Chinese passage not available")
            
            with tab2:
                if 'english' in passages:
                    english_ref, english_text = passages['english']
                    st.markdown(f"**{english_ref}**")
                    st.markdown(english_text)
                else:
                    st.info("English passage not available")




def _generate_lesson_plan(reference: str, client) -> dict | None:
    """
    Generate the two-layer lesson plan for a passage.
    Returns a parsed dict or None on failure.

    Added 2026-07-16 — BST Consolidation Plan step 4. Checks/populates the SAME
    st.session_state.shared_core_analysis cache Question Bank uses (see
    display_question_bank_interface() above) — whichever feature runs first for a given
    reference generates the analysis; whichever runs second for the SAME reference reuses
    it for free. This is the actual payoff step 4 exists to demonstrate: the shared
    analysis working across two different consumers, not just within one.

    Same fallback discipline as step 3: if the analysis call or parse fails, falls through
    to the original self-contained LESSON_PLAN_TEMPLATE (core_analysis=None) rather than
    blocking the feature.
    """
    from parsers import LessonPlanParser, CoreAnalysisParser

    # Get or reuse the shared core analysis for this reference.
    cached = st.session_state.get('shared_core_analysis')
    core_analysis_raw = None
    if cached and cached.get('reference') == reference:
        core_analysis_raw = cached.get('raw')  # reuse — no API call
    else:
        try:
            analysis_prompt = PromptTemplates.get_core_analysis_prompt(reference)
            analysis_raw = client.generate_content_quality(
                analysis_prompt,
                system_override=PromptTemplates.QUESTION_BANK_SYSTEM
            )
            parsed_analysis = CoreAnalysisParser.parse(analysis_raw)
            if CoreAnalysisParser.is_valid(parsed_analysis):
                core_analysis_raw = parsed_analysis['raw']
                st.session_state.shared_core_analysis = {
                    'reference': reference, 'raw': core_analysis_raw
                }
            else:
                logger.warning(
                    f"Core analysis parsed but invalid for {reference} "
                    f"(missing genre/central_claim) — falling back to "
                    f"self-contained lesson plan generation."
                )
        except Exception as e:
            logger.warning(
                f"Core analysis generation failed for {reference}: {e} — "
                f"falling back to self-contained lesson plan generation."
            )
            # core_analysis_raw stays None — falls through to the original path.

    prompt = PromptTemplates.get_lesson_plan_prompt(reference, core_analysis=core_analysis_raw)
    try:
        raw = client.generate_content_quality(prompt)
        parsed = LessonPlanParser.parse(raw)
        if LessonPlanParser.is_valid(parsed):
            return parsed
        else:
            logger.warning(f"Lesson plan parsed but incomplete for {reference}")
            logger.warning(f"Keys present: { {k: bool(v) for k, v in parsed.items()} }")
            return parsed  # Return partial — UI will handle missing sections
    except Exception as e:
        logger.error(f"Lesson plan generation failed: {e}")
        return None


# ── One-pass question bank display (Subtask 4, 2026-07-08) ────────────────────
# Basic display of the parsed, grouped question bank. NOT the full clickable/
# reference-only picker UI from the BST-to-BLT handoff vision (see NOTES.md
# "BST-to-BLT Handoff" section) — that is deliberately a later, separate piece
# of work. This is just enough to read the generated bank in a structured way,
# grouped by verse range with stacked levels shown together.
_LEVEL_DISPLAY = {
    "observation":   ("觀察", "Observation", "#2563eb"),   # blue
    "interpretation": ("詮釋", "Interpretation", "#7c3aed"), # purple
    "application":   ("應用", "Application", "#059669"),   # green
}

def display_question_bank_interface():
    """Generate and display the one-pass question bank, parsed and grouped
    by verse range, with stacked levels shown together within each group.

    Added 2026-07-14 — BST Consolidation Plan step 3: generates the shared core analysis
    ONCE per reference (cached in st.session_state.shared_core_analysis, invalidated when
    the reference changes at the entry point — see qbank_reference assignment below), then
    builds the question bank FROM that analysis via QUESTION_BANK_FROM_ANALYSIS_TEMPLATE,
    instead of each generation re-deriving genre/central claim/density map/misreadings/
    inter-unit relationships from scratch. "Regenerate" (below) intentionally reuses the
    cached analysis rather than forcing a fresh one — the passage's structure hasn't
    changed, only the specific question phrasing might benefit from a retry, and reusing
    the cache is exactly the saving this step exists for.

    UPDATED 2026-07-16 — step 4: this cache is no longer Question-Bank-specific.
    _generate_lesson_plan() (below) checks/populates the SAME shared_core_analysis key —
    whichever of the two features runs first for a given reference does the analysis; the
    other reuses it for free if run afterward for the same reference. This is the actual
    cross-feature payoff the whole consolidation plan was built toward.

    FALLBACK, not a hard requirement: if the core-analysis call or parse fails
    (CoreAnalysisParser.is_valid() False, or the API call itself errors), this falls back
    to the original self-contained QUESTION_BANK_TEMPLATE path (core_analysis=None) rather
    than blocking the feature — see NOTES.md "BST Consolidation Plan" for why step 2 was
    built additive/backward-compatible in the first place. This is that guarantee actually
    being exercised.
    """
    from parsers import QuestionBankParser, CoreAnalysisParser

    reference = st.session_state.get('qbank_reference', '')
    st.markdown(f"### 📚 問題庫 Question Bank — {reference}")
    st.caption("一次生成、依經文順序排列、避免重複的問題庫。"
               " A single-pass, verse-ordered, non-overlapping question bank.")

    raw = st.session_state.get('qbank_raw_result')
    if raw is None:
        client = st.session_state.gemini_client

        # Step 1 of 2 — get or reuse the shared core analysis for this reference.
        cached = st.session_state.get('shared_core_analysis')
        core_analysis_raw = None
        if cached and cached.get('reference') == reference:
            core_analysis_raw = cached.get('raw')  # reuse — no API call, no spinner needed
        else:
            with st.spinner("正在分析經文結構… Analysing passage structure…"):
                try:
                    analysis_prompt = PromptTemplates.get_core_analysis_prompt(reference)
                    analysis_raw = client.generate_content_quality(
                        analysis_prompt,
                        system_override=PromptTemplates.QUESTION_BANK_SYSTEM
                    )
                    parsed_analysis = CoreAnalysisParser.parse(analysis_raw)
                    if CoreAnalysisParser.is_valid(parsed_analysis):
                        core_analysis_raw = parsed_analysis['raw']
                        st.session_state.shared_core_analysis = {
                            'reference': reference, 'raw': core_analysis_raw
                        }
                    else:
                        logger.warning(
                            f"Core analysis parsed but invalid for {reference} "
                            f"(missing genre/central_claim) — falling back to "
                            f"self-contained question bank generation."
                        )
                except Exception as e:
                    logger.warning(
                        f"Core analysis generation failed for {reference}: {e} — "
                        f"falling back to self-contained question bank generation."
                    )
                    # core_analysis_raw stays None — falls through to the original path.

        # Step 2 of 2 — generate the bank, from the analysis if we have one, otherwise
        # the original self-contained template (same behaviour as before this step).
        prompt = PromptTemplates.get_question_bank_prompt(reference, core_analysis=core_analysis_raw)
        with st.spinner("正在生成問題庫… Generating question bank…"):
            try:
                raw = client.generate_content_quality(
                    prompt,
                    system_override=PromptTemplates.QUESTION_BANK_SYSTEM
                )
                st.session_state.qbank_raw_result = raw
                st.rerun()
            except Exception as e:
                logger.error(f"Question bank generation failed: {e}")
                st.error(f"生成失敗 Generation failed: {e}")
                if st.button("← 返回 Back"):
                    st.session_state.qbank_active = False
                    st.rerun()
                return

    parsed = QuestionBankParser.parse(raw)

    if not QuestionBankParser.is_valid(parsed):
        st.warning("問題庫解析失敗，顯示原始輸出。Parsing failed — showing raw output instead.")
        st.text_area("Raw output", value=raw, height=500)
    else:
        cc = st.session_state.cc_converter
        lang = st.radio(
            "顯示語言 Display language",
            options=["繁體中文", "简体中文", "English"],
            horizontal=True,
            key="qbank_lang_toggle"
        )

        groups = parsed["questions"]
        st.caption(f"共 {len(groups)} 個經文段落 · {len(QuestionBankParser.flat_list(parsed))} 個問題　"
                   f"({len(groups)} verse-range groups · {len(QuestionBankParser.flat_list(parsed))} questions total)")
        st.markdown("---")

        for group in groups:
            verse_label = f"v.{group['verse_range']}"
            st.markdown(f"#### 📖 {verse_label}")

            for level_key in ("observation", "interpretation", "application"):
                q = group["questions_by_level"].get(level_key)
                if not q:
                    continue
                label_zh, label_en, color = _LEVEL_DISPLAY[level_key]

                if lang == "English":
                    text = q["en"]
                    badge = label_en
                else:
                    text = q["zh"] if lang == "繁體中文" else cc.convert(q["zh"])
                    badge = label_zh

                st.markdown(
                    f'<div style="margin-bottom:0.3rem;">'
                    f'<span style="display:inline-block;font-size:0.75rem;font-weight:600;'
                    f'padding:0.15rem 0.5rem;border-radius:4px;margin-right:0.5rem;'
                    f'background:{color}20;color:{color};">{badge}</span>'
                    f'<span style="font-size:0.95rem;">{text}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                # Added 2026-07-16 — BST Consolidation Plan §4, Start Study retirement
                # build step 2. Single-select: clicking launches the new, parallel
                # sq_* flow (display_single_question_interface, below) with this
                # question pre-loaded. Deliberately a click-to-select button, not a
                # radio group + separate confirm — simplest possible selection UX,
                # matching the single-select-first decision in the plan document.
                if st.button("✏️ 回答這一題 Answer this",
                             key=f"sq_pick_{group['verse_range']}_{level_key}",
                             use_container_width=False):
                    st.session_state.sq_active = True
                    st.session_state.sq_reference = reference
                    st.session_state.sq_question = {
                        "verse_range": group["verse_range"],
                        "level": level_key,
                        "level_label_zh": label_zh,
                        "level_label_en": label_en,
                        "zh": q["zh"],
                        "en": q["en"],
                        "misread": q.get("misread"),
                    }
                    st.session_state.sq_bank_parsed = parsed  # for next_threads candidates
                    st.session_state.sq_answer = None
                    st.session_state.sq_feedback = None
                    st.session_state.sq_followup_question = None
                    st.session_state.sq_followup_answer = None
                    st.session_state.sq_followup_done = False
                    st.session_state.sq_reflection = None
                    st.rerun()
            st.markdown("---")

    # Raw output kept available for debugging, collapsed by default
    with st.expander("🔍 原始輸出 Raw output (debug)"):
        st.text_area("Raw", value=raw, height=400, key="qbank_raw_debug", label_visibility="collapsed")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 重新生成 Regenerate", use_container_width=True):
            st.session_state.qbank_raw_result = None
            st.rerun()
    with col2:
        st.download_button(
            "⬇️ 下載 Download",
            data=raw or "",
            file_name=f"qbank-{reference.replace(' ', '-').replace(':', '')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("---")
    if st.button("← 返回 Back", type="secondary"):
        st.session_state.qbank_active = False
        st.session_state.qbank_raw_result = None
        st.rerun()


def _select_next_threads_candidates(bank_parsed: dict, answered_question: dict, max_per_level: int = 2) -> str:
    """
    Added 2026-07-16 — BST Consolidation Plan §4, Start Study retirement build step 2.
    Programmatically selects 1-2 not-yet-answered bank questions per level, formatted for
    BST_REFLECTION_TEMPLATE's next_threads_candidates input. Deliberately NOT an LLM
    call — see NOTES.md "BST Consolidation Plan — Reflection Artifact Built" for why this
    stays programmatic (real, already-generated bank content, not invented) while the
    reflection's touched/deepen content is the part that genuinely needs an LLM.

    Excludes the answered question itself (matched on verse_range + level, which is
    unique within a single bank per QuestionBankParser's group structure).
    """
    if not bank_parsed:
        return ""
    flat = QuestionBankParser.flat_list(bank_parsed)
    answered_key = (answered_question["verse_range"], answered_question["level"])
    by_level = {"observation": [], "interpretation": [], "application": []}
    for q in flat:
        key = (q["verse_range"], q["level"])
        if key == answered_key:
            continue
        if len(by_level.get(q["level"], [])) < max_per_level:
            by_level[q["level"]].append(q)
    lines = []
    for level, items in by_level.items():
        for q in items:
            lines.append(f"[{level}] [V.{q['verse_range']}] {q['zh']}")
    return "\n".join(lines)


def display_single_question_interface():
    """
    Added 2026-07-16 — BST Consolidation Plan §4, Start Study retirement build step 2.
    New, PARALLEL flow for answering a single question selected from the Question Bank —
    built additively alongside the existing display_emphasis_interface() rather than
    editing it in place. The existing three-question emphasis quiz machinery
    (session_manager.py) is tightly coupled to a fixed observation→interpretation→
    application sequence; retrofitting single-select into it would fight that shape at
    every step. This function and its sq_* session-state keys are entirely separate,
    so the existing Start Study flow keeps working untouched while this is built and
    tested. See NOTES.md for the full reasoning.

    Mirrors display_emphasis_interface()'s evaluate → (bounded one-round followup/
    redirect if INCOMPLETE/INACCURATE) → final feedback pattern faithfully (that part
    is already well-designed, being reused deliberately, not reinvented) — but replaces
    the final "show raw feedback" step with generating and showing the new personalized
    reflection artifact (BST_REFLECTION_TEMPLATE / ReflectionParser) instead.
    """
    reference = st.session_state.sq_reference
    question = st.session_state.sq_question
    client = st.session_state.gemini_client

    st.markdown(f"### ✏️ {reference}")

    label_zh, label_en = question["level_label_zh"], question["level_label_en"]
    color = _LEVEL_DISPLAY.get(question["level"], (label_zh, label_en, "#8B7355"))[2]
    st.markdown(
        f'<div style="margin-bottom:1rem;">'
        f'<span style="display:inline-block;font-size:0.78rem;font-weight:700;'
        f'padding:0.2rem 0.6rem;border-radius:4px;margin-right:0.5rem;'
        f'background:{color}20;color:{color};">{label_zh} · {label_en}</span>'
        f'<span style="color:var(--text-muted);font-size:0.85rem;">V.{question["verse_range"]}</span>'
        f'</div>'
        f'<div class="question-card">'
        f'<div style="font-size:1.02rem;line-height:1.9;">{question["zh"]}</div>'
        f'<div style="font-size:0.85rem;color:var(--text-muted);margin-top:0.4rem;">{question["en"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── No answer yet — collect it ──
    if not st.session_state.sq_feedback:
        answer = st.text_area(
            "你的答案 Your Answer:", height=150, key="sq_answer_input",
            placeholder="在此輸入你的回答... / Type your answer here..."
        )
        if st.button("提交 Submit", type="primary", disabled=not answer.strip()):
            st.session_state.sq_answer = answer
            with st.spinner("正在評估... Evaluating..."):
                feedback = client.evaluate_answer(
                    reference=reference,
                    question_type=question["level"],
                    question=question["zh"],
                    user_answer=answer,
                    ai_answer=st.session_state.get('shared_core_analysis', {}).get('raw', ''),
                    emphasis="standard"  # build step 6 (emphasis toggle) not yet built — see plan
                )
                st.session_state.sq_feedback = feedback
            st.rerun()
        if st.button("← 返回 Back", type="secondary"):
            st.session_state.sq_active = False
            st.rerun()
        return

    # ── Evaluated — check for bounded one-round followup/redirect ──
    flag, note = QuizParser.parse_evaluation_flags(st.session_state.sq_feedback)
    needs_followup = flag in ('INCOMPLETE', 'INACCURATE') and not st.session_state.sq_followup_done

    if needs_followup:
        if not st.session_state.sq_followup_question:
            label = "思考一個跟進問題..." if flag == 'INCOMPLETE' else "回到經文看看..."
            with st.spinner(label):
                if flag == 'INCOMPLETE':
                    ch_q, en_q = client.generate_followup_question(
                        reference=reference, question_type=question["level"],
                        emphasis="standard", original_question=question["zh"],
                        user_answer=st.session_state.sq_answer, missing_note=note
                    )
                else:
                    ch_q, en_q = client.generate_redirect_question(
                        reference=reference, question_type=question["level"],
                        emphasis="standard", original_question=question["zh"],
                        user_answer=st.session_state.sq_answer, correction_note=note
                    )
                st.session_state.sq_followup_question = (ch_q, en_q)
            st.rerun()
        else:
            icon = "🔍" if flag == 'INCOMPLETE' else "📖"
            label = "跟進問題 Follow-up Question" if flag == 'INCOMPLETE' else "再看看經文 Look Again"
            st.markdown(f"### {icon} {label}")
            ch_q, en_q = st.session_state.sq_followup_question
            st.info(ch_q)
            if en_q:
                st.caption(en_q)
            followup_answer = st.text_area(
                "你的回應 Your response:", height=120, key="sq_followup_input"
            )
            if st.button("提交回應 Submit Response", type="primary",
                         disabled=not followup_answer.strip()):
                st.session_state.sq_followup_answer = followup_answer
                with st.spinner("重新評估... Re-evaluating..."):
                    fu_label = "follow-up" if flag == 'INCOMPLETE' else "re-read response"
                    combined_answer = (
                        f"Initial answer: {st.session_state.sq_answer}\n\n"
                        f"After {fu_label} question — additional response: {followup_answer}"
                    )
                    new_feedback = client.evaluate_answer(
                        reference=reference, question_type=question["level"],
                        question=question["zh"], user_answer=combined_answer,
                        ai_answer=st.session_state.get('shared_core_analysis', {}).get('raw', ''),
                        emphasis="standard"
                    )
                    st.session_state.sq_feedback = new_feedback
                    st.session_state.sq_followup_done = True
                st.rerun()
        return

    # ── Fully evaluated (no pending followup) — generate/show the reflection ──
    if not st.session_state.sq_reflection:
        with st.spinner("正在生成回顧... Generating your reflection..."):
            ch_feedback, _ = QuizParser.parse_evaluation_feedback(st.session_state.sq_feedback)
            candidates = _select_next_threads_candidates(
                st.session_state.get('sq_bank_parsed'), question
            )
            reflection_prompt = PromptTemplates.get_reflection_prompt(
                reference=reference, verse_range=question["verse_range"], level=label_zh,
                question=question["zh"], answer=st.session_state.sq_answer,
                eval_feedback=ch_feedback,
                eval_flag=flag, eval_note=note, next_threads_candidates=candidates
            )
            try:
                raw_reflection = client.generate_content_quality(reflection_prompt)
                parsed_reflection = ReflectionParser.parse(raw_reflection)
                if ReflectionParser.is_valid(parsed_reflection):
                    st.session_state.sq_reflection = parsed_reflection
                else:
                    logger.warning("Reflection generation produced invalid/unparseable output")
                    st.session_state.sq_reflection = {"_failed": True}
            except Exception as e:
                logger.error(f"Reflection generation failed: {e}")
                st.session_state.sq_reflection = {"_failed": True}
        st.rerun()

    reflection = st.session_state.sq_reflection
    st.success("✅ 已完成 Answered!")
    with st.expander("你的答案 Your Answer", expanded=False):
        st.write(st.session_state.sq_answer)

    if reflection.get("_failed"):
        st.info("回顧生成失敗，但你的答案已記錄。Reflection generation failed, but your answer was recorded.")
    else:
        st.markdown("### 🌿 你的學習回顧 Your Reflection")
        if reflection.get("touched"):
            for item in reflection["touched"]:
                st.markdown(f"✅ {item}")
        if reflection.get("deepen"):
            for item in reflection["deepen"]:
                st.markdown(f"↳ *{item}*")
        st.markdown(f"*{reflection.get('narrative_summary', '')}*")
        if reflection.get('narrative_summary_en'):
            st.caption(reflection['narrative_summary_en'])

        next_threads = reflection.get("next_threads", {})
        any_threads = any(next_threads.get(l) for l in ("observation", "interpretation", "application"))
        if any_threads:
            st.markdown("#### 繼續探索 Continue exploring")
            for level_key, level_label in [("observation", "觀察"), ("interpretation", "詮釋"), ("application", "應用")]:
                for item in next_threads.get(level_key, []):
                    st.markdown(f"→ **[{level_label}]** {item}")

    st.markdown("---")
    if st.button("📚 回到問題庫 Back to Question Bank", type="secondary"):
        st.session_state.sq_active = False
        st.rerun()


def display_lesson_plan_interface():
    """
    Display the two-layer lesson plan — facilitator guide + learner materials.
    Toggle between layers via a tab or toggle control.
    """
    from parsers import LessonPlanParser

    reference = st.session_state.lesson_plan_reference
    result = st.session_state.lesson_plan_result
    client = st.session_state.gemini_client
    cc = st.session_state.cc_converter

    st.markdown(f"### 📋 {reference} — 備課計劃 Lesson Plan")

    # ── Generate if not yet done ──────────────────────────────────────────
    if result is None:
        with st.spinner("正在生成備課計劃… Generating lesson plan…"):
            result = _generate_lesson_plan(reference, client)
        if result:
            st.session_state.lesson_plan_result = result
            st.rerun()
        else:
            st.error("備課計劃生成失敗，請重試。Lesson plan generation failed — please try again.")
            if st.button("← 返回 Back"):
                st.session_state.lesson_plan_active = False
                st.rerun()
            return

    # ── Layer toggle ──────────────────────────────────────────────────────
    layer = st.radio(
        "查看模式 View mode",
        options=["🔒 引導者備課資料 Facilitator Guide",
                 "📄 學員材料 Learner Materials"],
        horizontal=True,
        key="lesson_plan_layer_toggle"
    )
    st.markdown("---")

    is_facilitator = "引導者" in layer

    if is_facilitator:
        # ── LAYER 1: Facilitator Guide ────────────────────────────────────
        l1_ch = result.get("layer1_chinese", "")
        l1_en = result.get("layer1_english", "")

        if not l1_ch:
            st.warning("引導者備課資料未能生成。Facilitator guide section not available.")
        else:
            tab1, tab2, tab3 = st.tabs(["繁體中文", "简体中文", "English"])
            with tab1:
                st.markdown(l1_ch)
            with tab2:
                st.markdown(cc.convert(l1_ch))
            with tab3:
                st.markdown(l1_en or "")

    else:
        # ── LAYER 2: Learner Materials ────────────────────────────────────
        l2_ch = result.get("layer2_chinese", "")
        l2_en = result.get("layer2_english", "")

        if not l2_ch:
            st.warning("學員材料未能生成。Learner materials section not available.")
        else:
            tab1, tab2, tab3 = st.tabs(["繁體中文", "简体中文", "English"])
            with tab1:
                st.markdown(l2_ch)
            with tab2:
                st.markdown(cc.convert(l2_ch))
            with tab3:
                st.markdown(l2_en or "")

    st.markdown("---")

    # ── Download button ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        # Build full plain-text export
        full_text = f"# {reference} — 備課計劃 Lesson Plan\n\n"
        full_text += "=" * 60 + "\n"
        full_text += "## 引導者備課資料 FACILITATOR GUIDE\n"
        full_text += "=" * 60 + "\n\n"
        full_text += result.get("layer1_chinese", "") + "\n\n"
        full_text += result.get("layer1_english", "") + "\n\n"
        full_text += "=" * 60 + "\n"
        full_text += "## 學員材料 LEARNER MATERIALS\n"
        full_text += "=" * 60 + "\n\n"
        full_text += result.get("layer2_chinese", "") + "\n\n"
        full_text += result.get("layer2_english", "")
        filename = f"lesson-plan-{reference.replace(' ', '-').replace(':', '')}.txt"
        st.download_button(
            "⬇️ 下載完整計劃 Download Full Plan",
            data=full_text,
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )
    with col2:
        if st.button("🔄 重新生成 Regenerate", use_container_width=True):
            st.session_state.lesson_plan_result = None
            st.rerun()

    st.markdown("---")
    if st.button("← 返回 Back", type="secondary"):
        st.session_state.lesson_plan_active = False
        st.session_state.lesson_plan_result = None
        st.rerun()


def main():
    """Main application entry point."""
    # Check sandbox authentication first
    if not check_sandbox_authentication():
        st.stop()  # Stop execution if not authenticated
    
    # Initialize
    initialize_app()
    
    # Check if single-question mode is active (BST Consolidation Plan §4, Start Study
    # retirement build step 2, added 2026-07-16 — new, parallel flow, coexists with the
    # legacy emphasis flow below while under evaluation, same pattern as qbank_active
    # coexisting with emphasis_active did)
    if st.session_state.get('sq_active', False):
        display_single_question_interface()
    # Check if lesson plan mode is active
    elif st.session_state.lesson_plan_active:
        display_lesson_plan_interface()
    # Check if question bank mode is active (one-pass redesign — see NOTES.md
    # "One-Pass Question Bank" section, 2026-07-08. Not yet the default —
    # coexists with the legacy emphasis flow and the two-layer lesson plan
    # while under evaluation)
    elif st.session_state.get('qbank_active', False):
        display_question_bank_interface()
    # Check if emphasis mode is active
    elif st.session_state.emphasis_active:
        display_emphasis_interface()
    else:
        # Render UI and get inputs
        reference = render_ui()

        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("開始研讀 Start Study", type="primary", use_container_width=True):
                process_study_request(reference)
        with col2:
            if st.button("📋 生成備課計劃 Lesson Plan", type="secondary",
                         use_container_width=True,
                         help="生成引導者備課資料與學員材料的雙層計劃 / Generate a two-layer facilitator guide + learner materials"):
                ref = reference.strip() if reference else ""
                if ref:
                    st.session_state.lesson_plan_reference = ref
                    st.session_state.lesson_plan_active = True
                    st.session_state.lesson_plan_result = None
                    st.rerun()
                else:
                    st.warning("請先輸入聖經段落。Please enter a Bible reference first.")
        with col3:
            if st.button("📚 問題庫 Question Bank", type="secondary",
                         use_container_width=True,
                         help="一次生成、依經文順序、無重複的問題庫 / Generate a single-pass, verse-ordered, non-overlapping question bank"):
                ref = reference.strip() if reference else ""
                if ref:
                    st.session_state.qbank_reference = ref
                    st.session_state.qbank_active = True
                    st.session_state.qbank_raw_result = None
                    st.rerun()
                else:
                    st.warning("請先輸入聖經段落。Please enter a Bible reference first.")
    
    # Optional: Debug info (comment out for production)
    # SessionManager.show_debug_info()


if __name__ == "__main__":
    main()
