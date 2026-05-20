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


    @staticmethod
    def extract_understanding_confidence(response: str) -> tuple:
        """
        Extract AI's self-assessment of passage understanding.
        
        Args:
            response: Full AI response text
            
        Returns:
            Tuple of (confidence_score, reasoning) or (None, None) if not found
        """
        # Extract meta-assessment section
        meta_pattern = r'\[META_ASSESSMENT\](.*?)(?:\[|$)'
        meta_match = re.search(meta_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if not meta_match:
            return None, None
        
        meta_text = meta_match.group(1)
        
        # Extract confidence score
        confidence_pattern = r'Understanding Confidence:\s*(\d+)%'
        confidence_match = re.search(confidence_pattern, meta_text)
        
        # Extract reasoning
        reasoning_pattern = r'Reasoning:\s*(.+?)(?:\n\n|$)'
        reasoning_match = re.search(reasoning_pattern, meta_text, re.DOTALL)
        
        confidence = int(confidence_match.group(1)) if confidence_match else None
        reasoning = reasoning_match.group(1).strip() if reasoning_match else None
        
        return confidence, reasoning


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
    
    @staticmethod
    def parse_evaluation_flags(feedback_text: str) -> tuple:
        """
        Extract the evaluation flag and associated note from feedback text.

        The EVALUATION_TEMPLATE instructs the model to embed one of three flags
        in its response, along with an optional note that is forwarded to the
        follow-up / redirect question generators:

            [COMPLETE]
            [INCOMPLETE] [MISSING: <what was not covered>]
            [INACCURATE] [CORRECTION: <what was misunderstood>]

        Falls back to 'COMPLETE' if no flag is found so that the quiz can
        always proceed rather than hanging in a follow-up loop.

        Args:
            feedback_text: Raw evaluation feedback text

        Returns:
            Tuple of (flag, note) where:
              - flag: 'COMPLETE', 'INCOMPLETE', or 'INACCURATE'
              - note: detail string for follow-up/redirect prompt, or ''
        """
        if not feedback_text:
            return 'COMPLETE', ''

        # Order matters: check INCOMPLETE and INACCURATE before COMPLETE
        # to avoid COMPLETE matching inside e.g. [INCOMPLETE]
        incomplete_match = re.search(
            r'\[INCOMPLETE\](?:\s*\[MISSING:\s*(.+?)\])?',
            feedback_text, re.IGNORECASE | re.DOTALL
        )
        if incomplete_match:
            note = (incomplete_match.group(1) or '').strip()
            return 'INCOMPLETE', note

        inaccurate_match = re.search(
            r'\[INACCURATE\](?:\s*\[CORRECTION:\s*(.+?)\])?',
            feedback_text, re.IGNORECASE | re.DOTALL
        )
        if inaccurate_match:
            note = (inaccurate_match.group(1) or '').strip()
            return 'INACCURATE', note

        # COMPLETE — explicit or fallback
        return 'COMPLETE', ''

    @staticmethod
    def extract_score(feedback_text: str) -> Optional[int]:
        """
        Extract numerical score from feedback text.
        
        Args:
            feedback_text: Feedback text containing score in format "(得分: X/10, 信心度: Y%)" or "(Score: X/10, Confidence: Y%)"
            
        Returns:
            Score as integer, or None if not found
        """
        score_pattern = r'\((?:得分|Score):\s*(\d+)/10'
        match = re.search(score_pattern, feedback_text)
        
        if match:
            return int(match.group(1))
        return None
    
    @staticmethod
    def extract_confidence(feedback_text: str) -> Optional[int]:
        """
        Extract confidence percentage from feedback text.
        
        Args:
            feedback_text: Feedback text containing confidence in format "信心度: X%" or "Confidence: X%"
            
        Returns:
            Confidence as integer (0-100), or None if not found
        """
        confidence_pattern = r'(?:信心度|Confidence):\s*(\d+)%'
        match = re.search(confidence_pattern, feedback_text)
        
        if match:
            return int(match.group(1))
        return None
    
    @staticmethod
    def split_into_subquestions(question_text: str) -> list:
        """
        Split a question block into individual sub-questions.
        Each sentence ending with '?' is treated as a sub-question.
        Preserves the full sentence (including any leading context).

        Args:
            question_text: Full question text potentially containing multiple sub-questions

        Returns:
            List of sub-question strings. Returns [question_text] if no split needed.
        """
        import re
        # Split on both ASCII '?' and full-width Chinese '？' (U+FF1F)
        parts = re.split(r'(?<=[?？])\s*', question_text.strip())
        # Filter empty strings and strip whitespace
        subquestions = [p.strip() for p in parts if p.strip()]
        # Only return split result if there are genuinely multiple sub-questions
        return subquestions if len(subquestions) > 1 else [question_text.strip()]

    @staticmethod
    def extract_case_study(answer_key: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract threshold scenario from answer key.
        Looks for [THRESHOLD_SCENARIO_CHINESE] and [THRESHOLD_SCENARIO_ENGLISH] tags.

        Args:
            answer_key: Full answer key text that may contain threshold scenario sections

        Returns:
            Tuple of (chinese_scenario, english_scenario) or (None, None) if not found
        """
        # Extract Chinese threshold scenario
        ch_pattern = r'\[THRESHOLD_SCENARIO_CHINESE\](.*?)(?:\[THRESHOLD_SCENARIO_ENGLISH\]|\[META_ASSESSMENT\]|$)'
        ch_match = re.search(ch_pattern, answer_key, re.DOTALL | re.IGNORECASE)

        # Extract English threshold scenario
        en_pattern = r'\[THRESHOLD_SCENARIO_ENGLISH\](.*?)(?:\[META_ASSESSMENT\]|\[|$)'
        en_match = re.search(en_pattern, answer_key, re.DOTALL | re.IGNORECASE)

        ch_scenario = ch_match.group(1).strip() if ch_match else None
        en_scenario = en_match.group(1).strip() if en_match else None

        # Fallback: if tags not found but content exists, return full response as Chinese
        if not ch_scenario and answer_key and answer_key.strip():
            import logging
            logging.getLogger(__name__).warning(
                "extract_case_study: scenario tags not found — using full response as fallback"
            )
            ch_scenario = answer_key.strip()
            en_scenario = None

        return ch_scenario, en_scenario


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
    def render_emphasis_content(content: str, labels: dict):
        """
        Render emphasis question set — questions only, no summary section.
        Used for emphasis mode where the summary is displayed separately.
        """
        questions, _ = ResponseParser.extract_sections(content)
        st.markdown(questions or content)

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
