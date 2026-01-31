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
