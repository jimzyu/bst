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
from parsers import ResponseParser, ContentRenderer, QuizParser
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


def render_ui():
    """Render the main UI."""
    labels = Config.LABELS
    
    # Header
    st.title(labels['main_title'])
    st.subheader(labels['subtitle'])
    st.markdown(labels['input_prompt'])
    
    # Mode selection — Deep Study is the only option; Emphasis is the default
    deep_mode = st.checkbox(labels['deep_mode'],
                            help="運行三次平行分析以獲得更深入的問題組 / Run three parallel analyses for deeper question sets")
    
    st.markdown("---")
    
    # Input
    reference = st.text_input(
        labels['input_label'],
        placeholder=labels['input_placeholder']
    )
    
    return reference, deep_mode


def process_study_request(reference: str, deep_mode: bool):
    """
    Process a study request. Emphasis Study is always the default path.
    Deep Study runs three parallel analyses before presenting emphasis selection.
    
    Args:
        reference: Bible reference input
        deep_mode: Whether to use deep study mode for richer question generation
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
    
    # Always route to emphasis selection (with optional deep mode)
    try:
        process_emphasis_selection(reference, client, deep_mode=deep_mode)
            
    except GeminiAPIError as e:
        logger.error(f"API error: {str(e)}")
        SessionManager.record_error()
        st.error(f"API 錯誤 (API Error): {str(e)}")
        st.info("Please try again. If the problem persists, check your API key and quota.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        SessionManager.record_error()
        st.error(f"發生錯誤 (Error): {str(e)}")
        st.exception(e)


def process_emphasis_selection(reference: str, client, deep_mode: bool = False):
    """
    Generate all three emphasis question sets in parallel upfront,
    then show the selection screen. The user selects instantly with no wait.
    Deep mode runs three theological drafts first to inform richer questions.
    """
    if deep_mode:
        status_msg = "正在深度分析經文並準備問題組... Running deep analysis..."
    else:
        status_msg = "正在準備三種學習重點的問題組... Preparing all question sets..."

    with st.status(status_msg, expanded=True) as status:
        def cb(msg):
            status.update(label=f"生成中... {msg}")

        if deep_mode:
            # Deep mode: run three theological drafts in parallel first
            status.update(label="深度分析中 (1/3) — 標準神學分析...")
            prompts = PromptTemplates.get_threshold_deep_prompts(reference)
            drafts = client.generate_drafts_parallel(prompts, cb)
            theology_summary = "\n\n---\n\n".join(drafts)

            # Generate all three emphasis sets in parallel, enriched with theology
            status.update(label="深度分析中 (2/3) — 生成問題組...")
            emphasis_prompts = []
            emphasis_keys = ['explore', 'understand', 'apply']
            for emphasis in emphasis_keys:
                base_prompt = PromptTemplates.get_emphasis_prompt(reference, emphasis)
                enriched = (
                    f"THEOLOGICAL CONTEXT FROM PRIOR ANALYSIS "
                    f"(use this to enrich your questions — do NOT respond to it directly):\n"
                    f"{theology_summary[:3000]}\n\n"
                    f"---\n\n"
                    f"{base_prompt}\n\n"
                    f"REMINDER: Your response MUST begin immediately with the [CHINESE] tag. "
                    f"Do not write any preamble, acknowledgement, or prose before [CHINESE]."
                )
                emphasis_prompts.append(enriched)

            # Generate summary from drafts — all four in parallel
            summary_prompt = PromptTemplates.get_summary_from_drafts_prompt(
                reference, drafts[0], drafts[1], drafts[2])
            all_prompts = emphasis_prompts + [summary_prompt]
            all_results_list = client.generate_drafts_parallel(all_prompts, cb)

            all_results = {emphasis_keys[i]: all_results_list[i] for i in range(3)}
            summary_text = all_results_list[3]
            status.update(label="深度分析中 (3/3) — 整合完成...")
        else:
            all_results, summary_text = client.generate_all_emphasis_parallel(
                reference, status_callback=cb)

        SessionManager.start_emphasis(reference, all_results)
        st.session_state.emphasis_summary = summary_text

        status.update(label="✅ 準備完成！Ready.", state="complete", expanded=False)
    st.rerun()



def _build_scenario_prompt(reference, diagnosis, used_names):
    """Build a scenario prompt enriched with context and a randomised protagonist name.
    Reads context directly from Streamlit widget state — no Apply button needed.
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
    from prompts import PromptTemplates
    prefix = "請以繁體中文回應以下所有內容。\n\n"
    base = PromptTemplates.get_threshold_with_diagnosis_prompt(reference, diagnosis)
    return prefix + context_para + base

def display_emphasis_interface():
    """Display the emphasis study interface — selection, question set, or quiz."""
    from parsers import QuizParser

    EMPHASIS_OPTIONS = {
        'explore': {'label': '🔍 探索 Explore', 'desc': '讀讀看，注意你注意到什麼', 'desc_en': 'Read and notice what you notice'},
        'understand': {'label': '💡 理解 Understand', 'desc': '挖深一點，問為什麼', 'desc_en': 'Dig deeper, ask why'},
        'apply': {'label': '❤️ 應用 Apply', 'desc': '讓經文來問你', 'desc_en': 'Let the passage question you'},
    }

    reference = st.session_state.emphasis_reference
    selected = st.session_state.emphasis_selected
    result = st.session_state.emphasis_result
    client = st.session_state.gemini_client

    st.title("📖 選擇學習重點")
    st.markdown(f"**經文：** {reference}")
    st.markdown("---")

    # ── SCREEN 1: No emphasis selected yet ──
    if not selected or not result:
        st.markdown("### 今天你想怎麼讀這段經文？")
        st.markdown("*How do you want to approach this passage today?*")
        st.markdown("")
        cols = st.columns(3)
        for i, (key, opt) in enumerate(EMPHASIS_OPTIONS.items()):
            with cols[i]:
                st.markdown(f"**{opt['label']}**")
                st.markdown(f"*{opt['desc']}*")
                st.markdown(f"<small>{opt['desc_en']}</small>", unsafe_allow_html=True)
                if st.button(f"選擇 {opt['label']}", key=f"emphasis_{key}", use_container_width=True):
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

        st.markdown("---")

        # ── Passage Summary (collapsible reference panel with tabs) ──
        summary_raw = st.session_state.get('emphasis_summary')
        if summary_raw:
            ch_summary, en_summary = ResponseParser.parse_ai_response(summary_raw)
            with st.expander("📚 經文摘要 Passage Summary", expanded=False):
                stab1, stab2, stab3 = st.tabs(["繁體中文", "简体中文", "English"])
                with stab1:
                    st.markdown(ch_summary or summary_raw)
                with stab2:
                    sim_summary = st.session_state.cc_converter.convert(ch_summary or summary_raw)
                    st.markdown(sim_summary)
                with stab3:
                    st.markdown(en_summary or "")

        st.markdown("")

        # ── Case Study section ──
        from parsers import QuizParser
        case_study = st.session_state.emphasis_case_study
        teaching_points = st.session_state.emphasis_teaching_points
        tp_selected = st.session_state.emphasis_tp_selected

        if case_study:
            # ── State 3: Scenario already generated — show it ──

            # Debug: show raw TP mapping output if parsing failed and produced the fallback
            failed_raw = st.session_state.pop('_tp_map_failed_raw', None)
            if failed_raw:
                with st.expander("⚠️ Debug: Teaching point mapping returned 0 results — raw model output", expanded=True):
                    st.caption("Copy this and share it to fix the parser for this model.")
                    st.code(failed_raw, language=None)

            ch_case, en_case = case_study
            st.markdown("### 💡 情境案例 (Discussion Scenario)")
            tp_idx = st.session_state.emphasis_tp_selected
            if teaching_points and tp_idx is not None and tp_idx < len(teaching_points):
                tp = teaching_points[tp_idx]
                st.caption(f"📌 {tp['verses']} — {tp['teaching']}")
            ctab1, ctab2, ctab3 = st.tabs(["繁體中文", "简体中文", "English"])
            with ctab1:
                st.markdown(ch_case or "")
            with ctab2:
                sim_case = st.session_state.cc_converter.convert(ch_case or "")
                st.markdown(sim_case)
            with ctab3:
                st.markdown(en_case or "")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 換一個教學重點 Change teaching point", type="secondary"):
                    st.session_state.emphasis_case_study = None
                    st.session_state.emphasis_tp_selected = None
                    st.rerun()
            with col_b:
                if st.button("↩️ 重新生成 Regenerate", type="secondary"):
                    # Keep tp_selected — regenerate same teaching point immediately
                    tp_idx = st.session_state.emphasis_tp_selected
                    if tp_idx is not None and tp_idx < len(teaching_points):
                        tp = teaching_points[tp_idx]
                        with st.spinner("正在重新生成情境案例... Regenerating..."):
                            prompt = _build_scenario_prompt(
                                reference, tp['diagnosis'],
                                st.session_state.get('scenario_used_names', set())
                            )
                            raw = client.generate_content_quality(prompt)
                            ch_case, en_case = QuizParser.extract_case_study(raw)
                            st.session_state.emphasis_case_study = (ch_case, en_case)
                    st.rerun()

        elif teaching_points and tp_selected is None:
            # ── State 2: Teaching points mapped — show selection ──
            st.markdown("### 💡 情境案例 (Discussion Scenario)")

            # ── Persistent context selector ───────────────────────────────
            # Always visible, not collapsible — persists across all TPs
            REGIONS = ["灣區", "北美", "亞洲"]
            PROFS   = ["（不指定）", "科技業", "教育", "醫療", "商業", "全職父母", "教會事工"]
            STAGES  = ["（不指定）", "單身", "已婚無子", "育有子女", "空巢", "退休"]
            SCENES  = ["（不指定）", "職場", "學校", "家庭", "社區", "教會"]

            st.markdown("**⚙️ 情境設定 Scenario Context**")
            with st.container(border=True):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.selectbox("地區 Region", REGIONS, key="ctx_region")
                    st.selectbox("職業 Profession", PROFS, key="ctx_profession")
                with col_s2:
                    st.selectbox("人生階段 Life Stage", STAGES, key="ctx_life_stage")
                    st.selectbox("情境場景 Scene", SCENES, key="ctx_scene")

            st.markdown("**選擇今天要聚焦的教學重點：**")
            st.markdown("*Select the teaching point for today's session:*")
            st.markdown("")
            for i, tp in enumerate(teaching_points):
                col_tp, col_btn = st.columns([4, 1])
                with col_tp:
                    zh_label = tp.get('teaching_zh', '')
                    en_label = tp.get('teaching', '')
                    if zh_label:
                        st.markdown(
                            f"<div style='margin-bottom:12px'>"
                            f"<strong>教學重點 {i+1}</strong> "
                            f"<span style='color:#888'>({tp['verses']})</span><br>"
                            f"{zh_label}<br>"
                            f"<span style='font-size:0.85em;color:#888;font-style:italic'>{en_label}</span>"
                            f"</div>",
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f"<div style='margin-bottom:12px'>"
                            f"<strong>教學重點 {i+1}</strong> "
                            f"<span style='color:#888'>({tp['verses']})</span><br>"
                            f"<span style='font-size:0.85em'>{en_label}</span>"
                            f"</div>",
                            unsafe_allow_html=True)
                with col_btn:
                    if st.button(f"選擇\nSelect", key=f"tp_{i}", type="primary"):
                        with st.spinner("正在生成情境案例... Generating scenario..."):
                            prompt = _build_scenario_prompt(
                                reference, tp['diagnosis'],
                                st.session_state.get('scenario_used_names', set())
                            )
                            raw = client.generate_content_quality(prompt)
                            ch_case, en_case = QuizParser.extract_case_study(raw)
                            st.session_state.emphasis_case_study = (ch_case, en_case)
                            st.session_state.emphasis_tp_selected = i
                        st.rerun()
            st.markdown("")
            if st.button("✕ 取消 Cancel", type="secondary"):
                st.session_state.emphasis_teaching_points = []
                st.rerun()

        else:
            # ── State 1: Not yet mapped — show initial button ──
            if st.button("💡 生成情境案例 Generate Discussion Scenario", type="secondary"):
                with st.spinner("正在分析教學重點... Mapping teaching points..."):
                    points = client.map_passage_teaching_points(reference)
                    if points:
                        st.session_state.emphasis_teaching_points = points
                    else:
                        # Store raw output for debug display before falling back
                        st.session_state['_tp_map_failed_raw'] = getattr(
                            client, '_last_tp_raw', '(raw output not captured)')
                        # Fallback: generate directly without mapping
                        raw = client.generate_case_study(reference)
                        ch_case, en_case = QuizParser.extract_case_study(raw)
                        st.session_state.emphasis_case_study = (ch_case, en_case)
                st.rerun()

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
        st.markdown(f"### {type_labels.get(question_type, question_type)}")

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
                st.info(subquestions[0])

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




def main():
    """Main application entry point."""
    # Check sandbox authentication first
    if not check_sandbox_authentication():
        st.stop()  # Stop execution if not authenticated
    
    # Initialize
    initialize_app()
    
    # Check if emphasis mode is active
    if st.session_state.emphasis_active:
        display_emphasis_interface()
    else:
        # Render UI and get inputs
        reference, deep_mode = render_ui()
        
        # Process button click
        if st.button(Config.LABELS['button_text'], type="primary"):
            process_study_request(reference, deep_mode)
    
    # Optional: Debug info (comment out for production)
    # SessionManager.show_debug_info()


if __name__ == "__main__":
    main()
