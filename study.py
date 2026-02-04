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
    
    # DEBUG: Check secrets
    import streamlit as st
    st.write("DEBUG - Checking secrets:")
    st.write(f"GOOGLE_SHEETS_ID exists: {'GOOGLE_SHEETS_ID' in st.secrets}")
    st.write(f"google_service_account exists: {'google_service_account' in st.secrets}")
    if 'GOOGLE_SHEETS_ID' in st.secrets:
        st.write(f"Sheet ID: {st.secrets['GOOGLE_SHEETS_ID'][:20]}...")
    if 'google_service_account' in st.secrets:
        st.write(f"Service account fields: {list(st.secrets['google_service_account'].keys())}")
    
    # ... rest of function
    
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


def render_ui():
    """Render the main UI."""
    labels = Config.LABELS
    
    # Header
    st.title(labels['main_title'])
    st.subheader(labels['subtitle'])
    st.markdown(labels['input_prompt'])
    
    # Deep mode toggle
    deep_mode = st.checkbox(labels['deep_mode'])
    
    st.markdown("---")
    
    # Input
    reference = st.text_input(
        labels['input_label'],
        placeholder=labels['input_placeholder']
    )
    
    return reference, deep_mode


def process_study_request(reference: str, deep_mode: bool):
    """
    Process a study request.
    
    Args:
        reference: Bible reference input
        deep_mode: Whether to use deep study mode
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
        if deep_mode:
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
        
        # Save result
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


def main():
    """Main application entry point."""
    # Initialize
    initialize_app()
    
    # Render UI and get inputs
    reference, deep_mode = render_ui()
    
    # Process button click
    if st.button(Config.LABELS['button_text'], type="primary"):
        process_study_request(reference, deep_mode)
    
    # Display results
    display_results()
    
    # Optional: Debug info (comment out for production)
    # SessionManager.show_debug_info()


if __name__ == "__main__":
    main()
