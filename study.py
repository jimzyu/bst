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
from parsers import ResponseParser, ContentRenderer
from api_client import GeminiClient, GeminiAPIError
from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    
    # Mode selection
    col1, col2 = st.columns(2)
    with col1:
        deep_mode = st.checkbox(labels['deep_mode'])
    with col2:
        quiz_mode = st.checkbox('🎯 啟用問答學習模式 (Quiz Mode - Interactive Learning)')
    
    st.markdown("---")
    
    # Input
    reference = st.text_input(
        labels['input_label'],
        placeholder=labels['input_placeholder']
    )
    
    return reference, deep_mode, quiz_mode


def process_study_request(reference: str, deep_mode: bool, quiz_mode: bool):
    """
    Process a study request.
    
    Args:
        reference: Bible reference input
        deep_mode: Whether to use deep study mode
        quiz_mode: Whether to use quiz mode
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
    
    # Process based on mode
    try:
        if quiz_mode:
            process_quiz_mode(reference, deep_mode, client, labels)
        elif deep_mode:
            process_deep_study(reference, client, labels)
        else:
            process_standard_study(reference, client, labels)
            
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
        prompt = PromptTemplates.get_standard_prompt(reference)
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
        
        prompts = PromptTemplates.get_deep_prompts(reference)
        
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
        ch_text, en_text = ResponseParser.parse_ai_response(result)
        ContentRenderer.render_results(
            ch_text=ch_text,
            en_text=en_text,
            converter=st.session_state.cc_converter,
            labels=Config.LABELS
        )


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
        # Generate answer key (same as study mode, but hidden from user)
        if deep_mode:
            status.write("Generating comprehensive answer key with deep mode...")
            prompts = PromptTemplates.get_deep_prompts(reference)
            
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
            prompt = PromptTemplates.get_standard_prompt(reference)
            answer_key = client.generate_standard_study(reference, prompt)
        
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
        
        # Initialize quiz session
        SessionManager.start_quiz(
            reference=reference,
            answer_key=answer_key,
            questions=questions,
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
    
    # Check if quiz is complete
    if SessionManager.is_quiz_complete():
        display_quiz_summary()
        return
    
    # Get current question
    question_type = SessionManager.get_current_question_type()
    question_text = st.session_state.quiz_questions.get(question_type, "")
    
    # Question type labels
    type_labels = {
        "observation": "📖 Observation Question (觀察)",
        "interpretation": "🤔 Interpretation Question (解釋)",
        "application": "💡 Application Question (應用)"
    }
    
    # Display current question
    st.markdown(f"### {type_labels.get(question_type, question_type.title())}")
    st.info(question_text)
    
    # Check if this question has already been answered
    if question_type in st.session_state.quiz_feedbacks:
        # Show previous answer and feedback
        st.success("✅ You've answered this question!")
        
        with st.expander("📝 Your Answer"):
            st.write(st.session_state.quiz_user_answers[question_type])
        
        with st.expander("💬 Feedback"):
            feedback_text = st.session_state.quiz_feedbacks[question_type]
            ch_feedback, en_feedback = QuizParser.parse_evaluation_feedback(feedback_text)
            
            st.markdown("**中文反饋:**")
            st.markdown(ch_feedback)
            
            if en_feedback:
                st.markdown("**English Feedback:**")
                st.markdown(en_feedback)
        
        # Button to continue
        if st.button("Continue to Next Question ➡️", type="primary"):
            SessionManager.advance_to_next_question()
            st.rerun()
    
    else:
        # Input for user answer
        user_answer = st.text_area(
            "Your Answer (你的答案):",
            height=150,
            placeholder="Type your answer here... / 在此輸入你的答案..."
        )
        
        # Submit button
        if st.button("Submit Answer 提交答案", type="primary", disabled=not user_answer.strip()):
            with st.spinner("Evaluating your answer... 評估中..."):
                # Evaluate the answer
                client = st.session_state.gemini_client
                feedback = client.evaluate_answer(
                    reference=st.session_state.quiz_reference,
                    question_type=question_type,
                    question=question_text,
                    user_answer=user_answer,
                    ai_answer=st.session_state.quiz_answer_key
                )
                
                # Save answer and feedback
                SessionManager.save_quiz_answer(question_type, user_answer, feedback)
                
                # Log to Google Sheets (best effort - don't fail quiz if this errors)
                try:
                    if client.draft_logger and st.session_state.quiz_sheets_row:
                        client.draft_logger.log_quiz_answer(
                            row_number=st.session_state.quiz_sheets_row,
                            question_type=question_type,
                            user_answer=user_answer,
                            feedback=feedback
                        )
                except Exception as e:
                    logger.warning(f"Failed to log to Google Sheets, but quiz continues: {str(e)}")
                
                st.success("Answer submitted! ✅")
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
                with st.expander("English (NIrV)", expanded=False):
                    st.markdown(english_text)
    
    else:
        # Display as expander (for Study Mode)
        with st.expander("📖 View Bible Passage", expanded=False):
            tab1, tab2 = st.tabs(["中文 (FEB)", "English (NIrV)"])
            
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


def display_results():
    """Display study results if available."""
    result = SessionManager.get_current_result()
    
    if result:
        # Display Bible passage (expander for study mode)
        if 'last_reference' in st.session_state:
            display_bible_passage(st.session_state.last_reference, location="expander")
        
        ch_text, en_text = ResponseParser.parse_ai_response(result)
        ContentRenderer.render_results(
            ch_text=ch_text,
            en_text=en_text,
            converter=st.session_state.cc_converter,
            labels=Config.LABELS
        )


def main():
    """Main application entry point."""
    # Initialize
    initialize_app()
    
    # Check if quiz is active
    if st.session_state.quiz_active:
        # Display quiz interface
        display_quiz_interface()
    else:
        # Render UI and get inputs
        reference, deep_mode, quiz_mode = render_ui()
        
        # Process button click
        if st.button(Config.LABELS['button_text'], type="primary"):
            process_study_request(reference, deep_mode, quiz_mode)
        
        # Display results (only in study mode)
        if not quiz_mode:
            display_results()
    
    # Optional: Debug info (comment out for production)
    # SessionManager.show_debug_info()


if __name__ == "__main__":
    main()
