"""
Response parsing and content rendering utilities.
"""
import re
import streamlit as st
from typing import Optional, Tuple


class ResponseParser:
    """Parse and validate AI responses."""
    
    @staticmethod
    def is_invalid_reference(text: str) -> bool:
        """Check if response indicates invalid reference."""
        return "[INVALID_REF]" in text.upper()
    
    @staticmethod
    def parse_ai_response(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse AI response to extract Chinese and English content.
        
        Args:
            text: Raw AI response text
            
        Returns:
            Tuple of (chinese_content, english_content) or (None, None) if invalid
        """
        if ResponseParser.is_invalid_reference(text):
            return None, None
        
        # Patterns to extract sections
        ch_pattern = r"\[CHINESE\](.*?)\[ENGLISH\]"
        en_pattern = r"\[ENGLISH\](.*?)(?:\[|$)"
        
        ch_match = re.search(ch_pattern, text, re.DOTALL | re.IGNORECASE)
        en_match = re.search(en_pattern, text, re.DOTALL | re.IGNORECASE)
        
        # Extract content with fallbacks
        ch_content = ch_match.group(1).strip() if ch_match else text
        en_content = en_match.group(1).strip() if en_match else "English translation not available."
        
        return ch_content, en_content
    
    @staticmethod
    def extract_sections(content: str) -> Tuple[str, Optional[str]]:
        """
        Extract questions and summary sections from content.
        
        Args:
            content: Formatted content (Chinese or English)
            
        Returns:
            Tuple of (questions_section, summary_section)
        """
        # List of possible summary headers (both traditional and simplified Chinese, and English)
        summary_headers = [
            "### 主題摘要",  # Traditional Chinese
            "### 主题摘要",  # Simplified Chinese  
            "### Theme Summary"  # English
        ]
        
        questions = content
        summary = None
        
        # Find which header exists and split content
        for header in summary_headers:
            if header in content:
                parts = content.split(header, 1)
                questions = parts[0].strip()
                summary = parts[1].strip() if len(parts) > 1 else None
                break
        
        return questions, summary


class QuizParser:
    """Parse quiz-specific responses."""
    
    @staticmethod
    def extract_questions_from_study(study_text: str) -> dict:
        """
        Extract the three questions from a study guide.
        
        Args:
            study_text: Full study guide text with [CHINESE] section
            
        Returns:
            Dict of {question_type: question_text}
        """
        # Extract Chinese section
        ch_pattern = r"\[CHINESE\](.*?)\[ENGLISH\]"
        ch_match = re.search(ch_pattern, study_text, re.DOTALL | re.IGNORECASE)
        
        if not ch_match:
            return {}
        
        chinese_content = ch_match.group(1)
        
        # Extract individual questions
        questions = {}
        
        # Observation question
        obs_pattern = r"\*\*觀察[^:]*\*\*:\s*(.+?)(?=\d\.|###|$)"
        obs_match = re.search(obs_pattern, chinese_content, re.DOTALL)
        if obs_match:
            questions["observation"] = obs_match.group(1).strip()
        
        # Interpretation question
        int_pattern = r"\*\*解釋[^:]*\*\*:\s*(.+?)(?=\d\.|###|$)"
        int_match = re.search(int_pattern, chinese_content, re.DOTALL)
        if int_match:
            questions["interpretation"] = int_match.group(1).strip()
        
        # Application question
        app_pattern = r"\*\*應用[^:]*\*\*:\s*(.+?)(?=\d\.|###|$)"
        app_match = re.search(app_pattern, chinese_content, re.DOTALL)
        if app_match:
            questions["application"] = app_match.group(1).strip()
        
        return questions
    
    @staticmethod
    def parse_evaluation_feedback(feedback_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse evaluation feedback to extract Chinese and English sections.
        
        Args:
            feedback_text: Raw evaluation feedback with [CHINESE] and [ENGLISH] tags
            
        Returns:
            Tuple of (chinese_feedback, english_feedback)
        """
        ch_pattern = r"\[CHINESE\](.*?)\[ENGLISH\]"
        en_pattern = r"\[ENGLISH\](.*?)$"
        
        ch_match = re.search(ch_pattern, feedback_text, re.DOTALL | re.IGNORECASE)
        en_match = re.search(en_pattern, feedback_text, re.DOTALL | re.IGNORECASE)
        
        ch_feedback = ch_match.group(1).strip() if ch_match else feedback_text
        en_feedback = en_match.group(1).strip() if en_match else None
        
        return ch_feedback, en_feedback


class ContentRenderer:
    """Render study content in Streamlit UI."""
    
    @staticmethod
    def render_study_content(content: str, labels: dict):
        """
        Render study content with collapsible summary.
        
        Args:
            content: Formatted study content
            labels: Dictionary with UI label translations
        """
        questions, summary = ResponseParser.extract_sections(content)
        
        # Display questions section
        st.subheader(labels['reflections_title'])
        st.markdown(questions)
        
        # Display summary in expandable section if it exists
        if summary:
            with st.expander(labels['summary_expander']):
                st.markdown(summary)
    
    @staticmethod
    def render_error(labels: dict):
        """Render error message for invalid references."""
        st.error(labels['error_invalid'])
        st.info(labels['error_invalid_en'])
    
    @staticmethod
    def render_results(ch_text: Optional[str], en_text: Optional[str], 
                       converter, labels: dict):
        """
        Render complete results in tabs.
        
        Args:
            ch_text: Traditional Chinese content
            en_text: English content
            converter: OpenCC converter for traditional to simplified
            labels: Dictionary with UI labels
        """
        if ch_text is None:
            ContentRenderer.render_error(labels)
            return
        
        # Convert to simplified Chinese
        sim_text = converter.convert(ch_text)
        
        # Create tabs
        st.divider()
        tab1, tab2, tab3 = st.tabs([
            labels['tab_traditional'],
            labels['tab_simplified'],
            labels['tab_english']
        ])
        
        # Render content in each tab
        with tab1:
            ContentRenderer.render_study_content(ch_text, labels)
        
        with tab2:
            ContentRenderer.render_study_content(sim_text, labels)
        
        with tab3:
            ContentRenderer.render_study_content(en_text, labels)
