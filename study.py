"""
Bible Study Tool - Refactored Application
A Streamlit application for generating Bible study guides using Google Gemini AI.
"""
import streamlit as st
from opencc import OpenCC
import logging

# Local imports
from config import Config
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
    
    # Initialize Gemini client
    if 'gemini_client' not in st.session_state:
        api_key = Config.get_api_key()
        st.session_state.gemini_client = GeminiClient(
            api_key=api_key,
            system_instruction=PromptTemplates.SYSTEM_INSTRUCTION
        )
        logger.info("Application initialized successfully")
    
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
                enriched = f"THEOLOGICAL CONTEXT FROM PRIOR ANALYSIS:\n{theology_summary[:3000]}\n\n---\n\n{base_prompt}"
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
            ch_case, en_case = case_study
            st.markdown("### 💡 情境案例 (Discussion Scenario)")
            tp_idx = st.session_state.emphasis_tp_selected
            if teaching_points and tp_idx is not None and tp_idx < len(teaching_points):
                tp = teaching_points[tp_idx]
                st.caption(f"📌 {tp['verses']} — {tp['teaching']}")
            ctab1, ctab2 = st.tabs(["繁體中文", "English"])
            with ctab1:
                st.markdown(ch_case or "")
            with ctab2:
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
                            prefix = "請以繁體中文回應以下所有內容。\n\n"
                            raw = client.generate_content(
                                prefix +
                                PromptTemplates.get_threshold_with_diagnosis_prompt(
                                    reference, tp['diagnosis'])
                            )
                            ch_case, en_case = QuizParser.extract_case_study(raw)
                            st.session_state.emphasis_case_study = (ch_case, en_case)
                    st.rerun()

        elif teaching_points and tp_selected is None:
            # ── State 2: Teaching points mapped — show selection ──
            st.markdown("### 💡 情境案例 (Discussion Scenario)")
            st.markdown("**選擇今天要聚焦的教學重點：**")
            st.markdown("*Select the teaching point for today's session:*")
            st.markdown("")
            for i, tp in enumerate(teaching_points):
                col_tp, col_btn = st.columns([4, 1])
                with col_tp:
                    st.markdown(f"**{tp['verses']}** — {tp['teaching']}")
                with col_btn:
                    if st.button("選擇", key=f"tp_{i}", type="primary"):
                        with st.spinner("正在生成情境案例... Generating scenario..."):
                            prefix = "請以繁體中文回應以下所有內容。\n\n"
                            raw = client.generate_content(
                                prefix +
                                PromptTemplates.get_threshold_with_diagnosis_prompt(
                                    reference, tp['diagnosis'])
                            )
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
                        st.markdown(f"**Your answer:** {st.session_state.emphasis_quiz_answers.get(qtype, '')}")
                        feedback_text = st.session_state.emphasis_quiz_feedbacks[qtype]
                        ch_fb, _ = QuizParser.parse_evaluation_feedback(feedback_text)
                        st.markdown("**Feedback:**")
                        st.markdown(ch_fb)
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← 換一個重點 Try another emphasis", type="secondary"):
                    st.session_state.emphasis_selected = None
                    st.session_state.emphasis_result = None
                    st.session_state.emphasis_quiz_active = False
                    st.session_state.emphasis_quiz_question = 0
                    st.session_state.emphasis_quiz_feedbacks = {}
                    st.rerun()
            with col2:
                if st.button("✅ 完成 Done", type="primary"):
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
            st.success("✅ Answered!")
            collected = SessionManager.get_emphasis_subquestion_answers(question_type)
            for i, sq in enumerate(subquestions):
                with st.expander(f"Sub-question {i+1}" if total_subquestions > 1 else "Your Answer"):
                    st.markdown(f"**Q:** {sq}")
                    if i < len(collected):
                        st.write(collected[i])
            with st.expander("💬 Feedback"):
                feedback_text = st.session_state.emphasis_quiz_feedbacks[question_type]
                ch_fb, en_fb = QuizParser.parse_evaluation_feedback(feedback_text)
                st.markdown(ch_fb)
                if en_fb:
                    st.markdown("---")
                    st.markdown(en_fb)
            if st.button("Continue ➡️", type="primary"):
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

            user_answer = st.text_area(
                "Your Answer (你的答案):",
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



def process_standard_study(reference: str, client: GeminiClient, labels: dict):
    """
    Process standard study mode.
    
    Args:
        reference: Bible reference
        client: Gemini API client
        labels: UI labels dictionary
    """
    with st.status(labels['status_standard'], expanded=True) as status:
        # Generate study guide
        prompt = PromptTemplates.get_threshold_prompt(reference)
        result = client.generate_standard_study(reference, prompt)
        
        # Save result and reference
        st.session_state.last_reference = reference
        SessionManager.save_study_result(
            reference=reference,
            deep_mode=False,
            result=result
        )
        
        status.update(label=labels['status_complete'], state="complete", expanded=False)
        logger.info(f"Standard study completed for: {reference}")


def process_deep_study(reference: str, client: GeminiClient, labels: dict):
    """
    Process deep study mode (3 drafts + merge).
    
    Args:
        reference: Bible reference
        client: Gemini API client
        labels: UI labels dictionary
    """
    with st.status(labels['status_deep'], expanded=True) as status:
        
        def update_status(message: str):
            """Helper to update status message."""
            status.write(message)
        
        # Generate 3 drafts in parallel
        update_status("Draft 1: Standard Theological View...")
        update_status("Draft 2: Historical & Cultural Context...")
        update_status("Draft 3: Practical Life Application...")
        
        prompts = PromptTemplates.get_threshold_deep_prompts(reference)
        
        def build_merge_prompt(drafts: list) -> str:
            """Build the fully-formed merge prompt once drafts are available."""
            return PromptTemplates.get_merge_prompt(
                reference=reference,
                draft_1=drafts[0],
                draft_2=drafts[1],
                draft_3=drafts[2]
            )
        
        try:
            final_result = client.generate_deep_study(
                reference=reference,
                prompts=prompts,
                build_merge_prompt=build_merge_prompt,
                status_callback=update_status
            )
            
            # Check if invalid reference
            if "[INVALID_REF]" in final_result.upper():
                SessionManager.save_study_result(
                    reference=reference,
                    deep_mode=True,
                    result="[INVALID_REF]"
                )
                status.update(label="Error: Invalid Reference", state="error")
                logger.warning(f"Invalid reference in deep study: {reference}")
                return
            
            # Save result
            st.session_state.last_reference = reference
            SessionManager.save_study_result(
                reference=reference,
                deep_mode=True,
                result=final_result
            )
            
            status.update(label=labels['status_complete'], state="complete", expanded=False)
            logger.info(f"Deep study completed for: {reference}")
            
        except GeminiAPIError as e:
            SessionManager.save_study_result(
                reference=reference,
                deep_mode=True,
                result="",
                error=str(e)
            )
            status.update(label="Error", state="error")
            raise


def display_results():
    """Display study results if available."""
    result = SessionManager.get_current_result()
    
    if result:
        # Display Bible passage first (if available)
        if 'last_reference' in st.session_state:
            display_bible_passage(st.session_state.last_reference, location="expander")
        
        # Extract and display AI's understanding confidence
        confidence, reasoning = ResponseParser.extract_understanding_confidence(result)
        
        logger.info(f"Study mode - Confidence extracted: {confidence}")
        logger.info(f"Study mode - Reasoning extracted: {reasoning is not None}")
        
        if confidence is not None:
            # Determine color based on confidence level
            if confidence >= 90:
                color = "green"
                emoji = "✅"
            elif confidence >= 70:
                color = "blue"
                emoji = "ℹ️"
            elif confidence >= 50:
                color = "orange"
                emoji = "⚠️"
            else:
                color = "red"
                emoji = "⚠️"
            
            # Display confidence banner
            st.markdown(f"""
            <div style="background-color: rgba(100, 100, 100, 0.1); padding: 12px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 20px;">
                <div style="font-size: 18px; font-weight: bold; color: {color};">
                    {emoji} AI Understanding Confidence: {confidence}%
                </div>
                {f'<div style="font-size: 14px; color: #666; margin-top: 4px;">{reasoning}</div>' if reasoning else ''}
            </div>
            """, unsafe_allow_html=True)
        
        ch_text, en_text = ResponseParser.parse_ai_response(result)
        ContentRenderer.render_results(
            ch_text=ch_text,
            en_text=en_text,
            converter=st.session_state.cc_converter,
            labels=Config.LABELS
        )
        
        # Display discussion scenario after study results (if present)
        ch_case, en_case = QuizParser.extract_case_study(result)
        if ch_case or en_case:
            st.markdown("---")
            st.markdown("### 💡 情境案例 (Discussion Scenario)")
            
            with st.expander("📖 查看情境案例 / View Discussion Scenario", expanded=False):
                if ch_case:
                    st.markdown("**中文:**")
                    st.markdown(ch_case)
                if en_case:
                    st.markdown("---")
                    st.markdown("**English:**")
                    st.markdown(en_case)


def process_quiz_mode(reference: str, deep_mode: bool, client: GeminiClient, labels: dict):
    """
    Initialize quiz mode by generating answer key.
    
    Args:
        reference: Bible reference
        deep_mode: Whether to use deep mode for answer key generation
        client: Gemini API client
        labels: UI labels dictionary
    """
    from parsers import QuizParser
    
    with st.status("Generating quiz questions...", expanded=True) as status:
        # Generate answer key with threshold scenario
        if deep_mode:
            status.write("Generating comprehensive answer key with deep mode...")
            prompts = PromptTemplates.get_threshold_deep_prompts(reference)
            
            def build_merge_prompt(drafts: list) -> str:
                return PromptTemplates.get_merge_prompt(
                    reference=reference,
                    draft_1=drafts[0],
                    draft_2=drafts[1],
                    draft_3=drafts[2]
                )
            
            answer_key = client.generate_deep_study(
                reference=reference,
                prompts=prompts,
                build_merge_prompt=build_merge_prompt,
                status_callback=status.write
            )
        else:
            status.write("Generating answer key...")
            quiz_prompts = [PromptTemplates.get_threshold_prompt(reference)]
            answer_key = client.generate_standard_study(reference, quiz_prompts[0])
        
        # Check if invalid reference
        if "[INVALID_REF]" in answer_key.upper():
            st.error("❌ 無法識別該經文引用。請輸入有效的聖經章節。")
            st.info("Invalid scriptural reference. Please enter a valid Bible passage.")
            status.update(label="Error: Invalid Reference", state="error")
            return
        
        # Extract questions from answer key
        questions = QuizParser.extract_questions_from_study(answer_key)
        
        if not questions:
            st.error("Failed to extract questions from study guide. Please try again.")
            status.update(label="Error", state="error")
            return
        
        # Extract case study from answer key
        case_study = QuizParser.extract_case_study(answer_key)
        
        # Log case study extraction result
        if case_study and (case_study[0] or case_study[1]):
            logger.info(f"Case study extracted: CH={bool(case_study[0])}, EN={bool(case_study[1])}")
        
        # Log initial quiz to Google Sheets
        sheets_row = None
        if client.draft_logger:
            mode = "quiz_deep" if deep_mode else "quiz_standard"
            drafts = st.session_state.current_drafts if deep_mode else None
            sheets_row = client.draft_logger.log_quiz_initial(
                reference=reference,
                mode=mode,
                answer_key=answer_key,
                drafts=drafts
            )
        
        # Initialize quiz session with case study
        SessionManager.start_quiz(
            reference=reference,
            answer_key=answer_key,
            questions=questions,
            case_study=case_study,
            sheets_row=sheets_row
        )
        
        status.update(label="Quiz ready! ✅", state="complete", expanded=False)
        logger.info(f"Quiz initialized for: {reference}")
        
        # Trigger rerun to display quiz interface
        st.rerun()


def display_quiz_interface():
    """Display the interactive quiz interface."""
    from parsers import QuizParser
    
    if not st.session_state.quiz_active:
        return
    
    # Display Bible passage in sidebar for quiz mode
    if st.session_state.quiz_reference:
        display_bible_passage(st.session_state.quiz_reference, location="sidebar")
    
    st.markdown("---")
    st.subheader(f"📚 Quiz: {st.session_state.quiz_reference}")
    
    # Display AI's understanding confidence at the start of quiz
    if st.session_state.quiz_answer_key:
        confidence, reasoning = ResponseParser.extract_understanding_confidence(st.session_state.quiz_answer_key)
        
        if confidence is not None:
            if confidence >= 90:
                color = "green"
                emoji = "✅"
            elif confidence >= 70:
                color = "blue"
                emoji = "ℹ️"
            elif confidence >= 50:
                color = "orange"
                emoji = "⚠️"
            else:
                color = "red"
                emoji = "⚠️"
            
            st.markdown(f"""
            <div style="background-color: rgba(100, 100, 100, 0.1); padding: 12px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 15px;">
                <div style="font-size: 18px; font-weight: bold; color: {color};">
                    {emoji} AI Understanding Confidence: {confidence}%
                </div>
                {f'<div style="font-size: 14px; color: #666; margin-top: 4px;">{reasoning}</div>' if reasoning else ''}
            </div>
            """, unsafe_allow_html=True)
    
    # Check if quiz is complete
    if SessionManager.is_quiz_complete():
        display_quiz_summary()
        return
    
    # Get current question
    question_type = SessionManager.get_current_question_type()
    question_text = st.session_state.quiz_questions.get(question_type, "")
    
    # Split question into sub-questions
    subquestions = QuizParser.split_into_subquestions(question_text)
    total_subquestions = len(subquestions)
    current_sub_idx = st.session_state.quiz_current_subquestion
    
    # Question type labels
    type_labels = {
        "observation": "📖 Observation Question (觀察)",
        "interpretation": "🤔 Interpretation Question (解釋)",
        "application": "💡 Application Question (應用)"
    }
    
    st.markdown(f"### {type_labels.get(question_type, question_type.title())}")
    
    # --- Case: this question has already been fully evaluated (feedback stored) ---
    if question_type in st.session_state.quiz_feedbacks:
        st.success("✅ You've answered this question!")
        
        # Show all sub-questions and their answers
        collected_answers = SessionManager.get_subquestion_answers(question_type)
        for i, sq in enumerate(subquestions):
            with st.expander(f"📝 Sub-question {i+1}" if total_subquestions > 1 else "📝 Your Answer"):
                st.markdown(f"**Question:** {sq}")
                if i < len(collected_answers):
                    st.write(collected_answers[i])
        
        with st.expander("💬 Feedback"):
            feedback_text = st.session_state.quiz_feedbacks[question_type]
            ch_feedback, en_feedback = QuizParser.parse_evaluation_feedback(feedback_text)
            
            st.markdown("**中文反饋:**")
            st.markdown(ch_feedback)
            
            if en_feedback:
                st.markdown("**English Feedback:**")
                st.markdown(en_feedback)
        
        # Show discussion scenario after Application question
        if question_type == "application":
            if st.session_state.quiz_case_study:
                ch_case, en_case = st.session_state.quiz_case_study
                if ch_case or en_case:
                    st.markdown("---")
                    st.markdown("### 💡 情境案例 (Discussion Scenario)")
                    with st.expander("📖 查看情境案例 / View Discussion Scenario", expanded=True):
                        if ch_case:
                            st.markdown("**中文:**")
                            st.markdown(ch_case)
                        if en_case:
                            st.markdown("**English:**")
                            st.markdown(en_case)
        
        if st.button("Continue to Next Question ➡️", type="primary"):
            SessionManager.advance_to_next_question()
            st.rerun()
    
    # --- Case: still collecting sub-question answers ---
    elif current_sub_idx < total_subquestions:
        collected_answers = SessionManager.get_subquestion_answers(question_type)

        if total_subquestions > 1:
            # Show ALL sub-questions upfront so the user knows what's coming
            st.markdown("**Questions for this section:**")
            for i, sq in enumerate(subquestions):
                if i < current_sub_idx:
                    # Already answered — show question + answer compactly
                    st.markdown(
                        f"<div style='padding:8px 12px; border-left:3px solid #4CAF50; margin-bottom:8px; opacity:0.75;'>"
                        f"<strong>{i+1}. {sq}</strong><br>"
                        f"<em style='color:#555;'>Your answer: {collected_answers[i]}</em></div>",
                        unsafe_allow_html=True
                    )
                elif i == current_sub_idx:
                    # Active sub-question — highlighted
                    st.markdown(
                        f"<div style='padding:8px 12px; border-left:3px solid #2196F3; background:rgba(33,150,243,0.07); margin-bottom:8px;'>"
                        f"<strong>{i+1}. {sq}</strong> ◀ <em>Answer this now</em></div>",
                        unsafe_allow_html=True
                    )
                else:
                    # Upcoming sub-questions — greyed out
                    st.markdown(
                        f"<div style='padding:8px 12px; border-left:3px solid #ccc; margin-bottom:8px; opacity:0.5;'>"
                        f"<strong>{i+1}. {sq}</strong></div>",
                        unsafe_allow_html=True
                    )
            st.markdown("")
        else:
            # Single sub-question — simple display
            st.info(subquestions[0])

        user_answer = st.text_area(
            "Your Answer (你的答案):",
            height=150,
            placeholder="Type your answer here... / 在此輸入你的答案...",
            key=f"answer_{question_type}_{current_sub_idx}"
        )

        is_last_subquestion = (current_sub_idx == total_subquestions - 1)
        btn_label = "Submit Answer 提交答案" if is_last_subquestion else "Next Sub-question ➡️"

        if st.button(btn_label, type="primary", disabled=not user_answer.strip()):
            # Save this sub-question's answer
            SessionManager.save_subquestion_answer(question_type, user_answer)

            if is_last_subquestion:
                # All sub-questions answered — evaluate with ONE API call
                all_answers = SessionManager.get_subquestion_answers(question_type)
                combined_user_answer = "\n\n".join(
                    f"Sub-question {i+1}: {ans}" for i, ans in enumerate(all_answers)
                ) if total_subquestions > 1 else all_answers[0]

                combined_question = "\n".join(
                    f"{i+1}. {sq}" for i, sq in enumerate(subquestions)
                ) if total_subquestions > 1 else subquestions[0]

                with st.spinner("Evaluating your answers... 評估中..."):
                    client = st.session_state.gemini_client
                    feedback = client.evaluate_answer(
                        reference=st.session_state.quiz_reference,
                        question_type=question_type,
                        question=combined_question,
                        user_answer=combined_user_answer,
                        ai_answer=st.session_state.quiz_answer_key
                    )

                    # Save feedback under question_type (signals this question is fully done)
                    SessionManager.save_quiz_answer(question_type, combined_user_answer, feedback)

                    # Log to Google Sheets
                    try:
                        if client.draft_logger and st.session_state.quiz_sheets_row:
                            client.draft_logger.log_quiz_answer(
                                row_number=st.session_state.quiz_sheets_row,
                                question_type=question_type,
                                user_answer=combined_user_answer,
                                feedback=feedback
                            )
                    except Exception as e:
                        logger.warning(f"Failed to log to Google Sheets, but quiz continues: {str(e)}")

                st.success("Answer submitted! ✅")
                st.rerun()
            else:
                # Move to next sub-question — no API call
                SessionManager.advance_to_next_subquestion()
                st.rerun()


def display_quiz_summary():
    """Display summary after completing all quiz questions."""
    st.success("🎉 Congratulations! You've completed the quiz!")
    
    st.markdown("### 📊 Quiz Summary")
    
    # Display all questions, answers, and feedback
    question_types = ["observation", "interpretation", "application"]
    type_labels = {
        "observation": "📖 Observation (觀察)",
        "interpretation": "🤔 Interpretation (解釋)",
        "application": "💡 Application (應用)"
    }
    
    from parsers import QuizParser
    
    # Display detailed feedback for each question (score is in parentheses at end of feedback)
    for qtype in question_types:
        if qtype in st.session_state.quiz_user_answers:
            with st.expander(f"{type_labels[qtype]}", expanded=False):
                st.markdown(f"**Question:** {st.session_state.quiz_questions[qtype]}")
                st.markdown(f"**Your Answer:** {st.session_state.quiz_user_answers[qtype]}")
                
                feedback_text = st.session_state.quiz_feedbacks[qtype]
                ch_feedback, en_feedback = QuizParser.parse_evaluation_feedback(feedback_text)
                
                st.markdown("**Feedback (反饋):**")
                st.markdown(ch_feedback)
    
    # Option to see AI's full answer
    if st.button("📖 View AI's Complete Study Guide", type="secondary"):
        st.markdown("---")
        st.markdown("### AI's Complete Answer Key")
        ch_text, en_text = ResponseParser.parse_ai_response(st.session_state.quiz_answer_key)
        
        tab1, tab2, tab3 = st.tabs(["繁體中文", "简体中文", "English"])
        
        with tab1:
            st.markdown(ch_text)
        with tab2:
            sim_text = st.session_state.cc_converter.convert(ch_text)
            st.markdown(sim_text)
        with tab3:
            st.markdown(en_text)
    
    # Button to end quiz
    if st.button("🔄 Start New Quiz", type="primary"):
        SessionManager.end_quiz()
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
