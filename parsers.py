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

        Defensive against common model output variations:
        - [CHINESE] tag missing (model prefixed prose or omitted tag)
        - [META_ASSESSMENT] appearing between [CHINESE] and [ENGLISH]
        - Full-width colons （：） instead of ASCII colons
        - Theological context block prepended before [CHINESE]
        - Multi-line sub-questions under a single label

        Args:
            study_text: Full study guide text

        Returns:
            Dict of {question_type: question_text}, empty dict if nothing found
        """
        if not study_text:
            return {}

        # Step 1: isolate the Chinese section if tags are present.
        # Stop at [META_ASSESSMENT] or [ENGLISH] — whichever comes first —
        # so a [META_ASSESSMENT] block between [CHINESE] and [ENGLISH] doesn't
        # swallow the question content.
        ch_pattern = r"\[CHINESE\](.*?)(?=\[ENGLISH\]|\[META_ASSESSMENT\])"
        ch_match = re.search(ch_pattern, study_text, re.DOTALL | re.IGNORECASE)
        content = ch_match.group(1).strip() if ch_match else study_text

        # Step 2: match question labels.
        # Handles both ASCII (:) and full-width (：) colons, with or without
        # the English gloss in parentheses, with or without a leading number.
        obs_pattern = (
            r"\*\*觀察[^*]*\*\*[：:]\s*"
            r"(.+?)"
            r"(?=\n\s*(?:\d+\.)?\s*\*\*(?:解釋|應用)|\Z)"
        )
        int_pattern = (
            r"\*\*解釋[^*]*\*\*[：:]\s*"
            r"(.+?)"
            r"(?=\n\s*(?:\d+\.)?\s*\*\*(?:應用|觀察)|\Z)"
        )
        app_pattern = (
            r"\*\*應用[^*]*\*\*[：:]\s*"
            r"(.+?)"
            r"(?=\n\s*(?:\d+\.)?\s*\*\*(?:觀察|解釋)"
            r"|\[ENGLISH\]|\[META_ASSESSMENT\]|\Z)"
        )

        questions = {}
        obs  = re.search(obs_pattern,  content, re.DOTALL)
        intr = re.search(int_pattern,  content, re.DOTALL)
        app  = re.search(app_pattern,  content, re.DOTALL)

        if obs:  questions["observation"]    = obs.group(1).strip()
        if intr: questions["interpretation"] = intr.group(1).strip()
        if app:  questions["application"]    = app.group(1).strip()

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

        The EVALUATION_TEMPLATE instructs the model to embed one of four flags
        in its response, along with an optional note that is forwarded to the
        follow-up / redirect question generators:

            [COMPLETE]
            [INCOMPLETE] [MISSING: <what was not covered>]
            [DEFENSIBLE_ALTERNATE] [NOTE: <alternate reading and why it's defensible>]
            [INACCURATE] [CORRECTION: <what was misunderstood>] [PATTERN: <named reasoning error, or 'general'>]

        DEFENSIBLE_ALTERNATE added 2026-07-14 (see NOTES.md "BST 承認無知" entry) — a
        genuinely contested interpretive point where the student's answer differs from
        the model's own default reading but is textually defensible, not an error. Treated
        like COMPLETE for follow-up purposes (see study.py — not in the INCOMPLETE/INACCURATE
        tuple that triggers a redirect loop), but returned as its own explicit flag rather
        than silently falling through to COMPLETE, so the distinction is preserved for
        anyone inspecting the raw flag later (e.g. analytics, or a future UI treatment).

        PATTERN added the same day — when INACCURATE fires, the model names which of six
        known reasoning-error patterns fits (斷章取義/以偏概全/同一律/argument-from-silence/
        root-fallacy/forced-harmonization), folded into the returned note so the existing
        2-tuple contract doesn't change for callers, giving REDIRECT_QUESTION_TEMPLATE a more
        precisely-targeted correction_note without any call-site changes.

        Falls back to 'COMPLETE' if no flag is found so that the quiz can
        always proceed rather than hanging in a follow-up loop.

        Args:
            feedback_text: Raw evaluation feedback text

        Returns:
            Tuple of (flag, note) where:
              - flag: 'COMPLETE', 'INCOMPLETE', 'DEFENSIBLE_ALTERNATE', or 'INACCURATE'
              - note: detail string for follow-up/redirect prompt, or ''
        """
        if not feedback_text:
            return 'COMPLETE', ''

        # Order matters: check INCOMPLETE, DEFENSIBLE_ALTERNATE, and INACCURATE before
        # COMPLETE, to avoid COMPLETE matching inside e.g. [INCOMPLETE]
        incomplete_match = re.search(
            r'\[INCOMPLETE\](?:\s*\[MISSING:\s*(.+?)\])?',
            feedback_text, re.IGNORECASE | re.DOTALL
        )
        if incomplete_match:
            note = (incomplete_match.group(1) or '').strip()
            return 'INCOMPLETE', note

        alternate_match = re.search(
            r'\[DEFENSIBLE_ALTERNATE\](?:\s*\[NOTE:\s*(.+?)\])?',
            feedback_text, re.IGNORECASE | re.DOTALL
        )
        if alternate_match:
            note = (alternate_match.group(1) or '').strip()
            return 'DEFENSIBLE_ALTERNATE', note

        inaccurate_match = re.search(
            r'\[INACCURATE\](?:\s*\[CORRECTION:\s*(.+?)\])?(?:\s*\[PATTERN:\s*(.+?)\])?',
            feedback_text, re.IGNORECASE | re.DOTALL
        )
        if inaccurate_match:
            correction = (inaccurate_match.group(1) or '').strip()
            pattern = (inaccurate_match.group(2) or '').strip()
            if pattern and pattern.lower() != 'general':
                note = f"（常見錯誤類型 pattern: {pattern}）{correction}" if correction else f"（pattern: {pattern}）"
            else:
                note = correction
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
        import logging
        _logger = logging.getLogger(__name__)

        # Extract Chinese threshold scenario
        ch_pattern = r'\[THRESHOLD_SCENARIO_CHINESE\](.*?)(?:\[THRESHOLD_SCENARIO_ENGLISH\]|\[META_ASSESSMENT\]|$)'
        ch_match = re.search(ch_pattern, answer_key, re.DOTALL | re.IGNORECASE)

        # Extract English threshold scenario
        en_pattern = r'\[THRESHOLD_SCENARIO_ENGLISH\](.*?)(?:\[META_ASSESSMENT\]|\[|$)'
        en_match = re.search(en_pattern, answer_key, re.DOTALL | re.IGNORECASE)

        ch_scenario = ch_match.group(1).strip() if ch_match else None
        en_scenario = en_match.group(1).strip() if en_match else None

        # Truncation detection: scenario present but ends abruptly without discussion questions
        if ch_scenario:
            has_q1 = '討論問題' in ch_scenario or 'Q1' in ch_scenario or '1.' in ch_scenario[-200:]
            has_q2 = 'Q2' in ch_scenario or ('2.' in ch_scenario[-200:])
            if not has_q1:
                _logger.warning(
                    "extract_case_study: scenario appears truncated — "
                    "discussion questions not found in Chinese scenario. "
                    f"Last 100 chars: {repr(ch_scenario[-100:])}"
                )

        # Fallback: if tags not found but content exists, return full response as Chinese
        if not ch_scenario and answer_key and answer_key.strip():
            _logger.warning(
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


class LessonPlanParser:
    """Parser for two-layer lesson plan output."""

    # Tags that delimit the four sections
    TAG_L1_CH = "[LESSON_PLAN_LAYER1_CHINESE]"
    TAG_L1_EN = "[LESSON_PLAN_LAYER1_ENGLISH]"
    TAG_L2_CH = "[LESSON_PLAN_LAYER2_CHINESE]"
    TAG_L2_EN = "[LESSON_PLAN_LAYER2_ENGLISH]"

    @classmethod
    def parse(cls, raw: str) -> dict:
        """
        Parse the two-layer lesson plan output into four sections.

        Returns a dict with keys:
            layer1_chinese, layer1_english,
            layer2_chinese, layer2_english
        Each value is a string (may be empty string if tag not found).
        """
        def _between(text: str, start_tag: str, end_tag: str) -> str:
            start = text.find(start_tag)
            if start == -1:
                return ""
            start += len(start_tag)
            end = text.find(end_tag, start)
            if end == -1:
                return text[start:].strip()
            return text[start:end].strip()

        layer1_ch = _between(raw, cls.TAG_L1_CH, cls.TAG_L1_EN)
        layer1_en = _between(raw, cls.TAG_L1_EN, cls.TAG_L2_CH)
        layer2_ch = _between(raw, cls.TAG_L2_CH, cls.TAG_L2_EN)
        layer2_en = _between(raw, cls.TAG_L2_EN, "\n\n\n")
        if not layer2_en:
            # Fallback: everything after the last tag
            last_tag_pos = raw.rfind(cls.TAG_L2_EN)
            if last_tag_pos != -1:
                layer2_en = raw[last_tag_pos + len(cls.TAG_L2_EN):].strip()

        return {
            "layer1_chinese": layer1_ch,
            "layer1_english": layer1_en,
            "layer2_chinese": layer2_ch,
            "layer2_english": layer2_en,
        }

    @classmethod
    def is_valid(cls, parsed: dict) -> bool:
        """Check that all four sections have content."""
        return all(parsed.get(k) for k in [
            "layer1_chinese", "layer1_english",
            "layer2_chinese", "layer2_english"
        ])


class QuestionBankParser:
    """
    Parser for the one-pass question bank output (see prompts.py
    QUESTION_BANK_TEMPLATE / get_question_bank_prompt).

    Handles:
    - Contiguous verse tags: [V.1-5]
    - Single-verse tags: [V.27]
    - Non-contiguous verse tags: [V.24, 26, 28], [V.1, 6-7]
    - Multiple questions stacked on the same verse range (same-range depth —
      e.g. an observation, interpretation, and application question all
      targeting [V.1-12]) — these are grouped together, not treated as
      unrelated independent items, per the parser requirement identified
      during Subtask 2 testing (see NOTES.md 2026-07-08).
    """

    TAG_CHINESE = "[QUESTION_BANK_CHINESE]"
    TAG_ENGLISH = "[QUESTION_BANK_ENGLISH]"

    # Matches: [V.<verse spec>] [<level>] <question text, up to the next
    # [V....] [...] tag or end of string>. DOTALL so a question may itself
    # span multiple lines without breaking the match.
    _QUESTION_PATTERN = re.compile(
        r'\[V\.([^\]]+)\]\s*\[([^\]]+)\]\s*(.+?)(?=\n*\[V\.[^\]]+\]\s*\[|\Z)',
        re.DOTALL
    )

    # Normalises whichever level label the model used (Chinese or English,
    # either language's section) to one canonical internal key.
    _LEVEL_MAP = {
        '觀察': 'observation', 'observation': 'observation',
        '詮釋': 'interpretation', 'interpretation': 'interpretation',
        '應用': 'application', 'application': 'application',
    }

    @classmethod
    def _extract_section(cls, text: str) -> list[dict]:
        """Extract all [V.x] [level] question entries from one language section."""
        results = []
        for verse_range, level_raw, question in cls._QUESTION_PATTERN.findall(text):
            level_key = cls._LEVEL_MAP.get(level_raw.strip(), level_raw.strip().lower())
            results.append({
                "verse_range": verse_range.strip(),
                "level": level_key,
                "level_label": level_raw.strip(),  # original label, for display
                "question": question.strip(),
            })
        return results

    @classmethod
    def parse(cls, raw: str) -> dict:
        """
        Parse the one-pass question bank output.

        Returns a dict:
            {
                "questions": [
                    {
                        "verse_range": "1-12",
                        "questions_by_level": {
                            "observation": {"zh": "...", "en": "..."} | None,
                            "interpretation": {"zh": "...", "en": "..."} | None,
                            "application": {"zh": "...", "en": "..."} | None,
                        }
                    },
                    ...
                ]
            }
        Ordered by first appearance in the Chinese section (verse position,
        per the prompt's ordering rule). Each verse_range group may contain
        one, two, or three levels depending on how much depth that range
        received (same-range stacking — see NOTES.md 2026-07-08).
        Returns {"questions": []} if parsing fails or no questions found.
        """
        ch_start = raw.find(cls.TAG_CHINESE)
        en_start = raw.find(cls.TAG_ENGLISH)

        if ch_start == -1 or en_start == -1:
            return {"questions": []}

        ch_text = raw[ch_start + len(cls.TAG_CHINESE):en_start]
        en_text = raw[en_start + len(cls.TAG_ENGLISH):]

        ch_entries = cls._extract_section(ch_text)
        en_entries = cls._extract_section(en_text)

        # Pair Chinese and English entries by position (same order, per
        # the prompt's instruction that both sections list questions in
        # identical sequence). If counts mismatch, pair what we can and
        # log the shortfall rather than failing outright.
        paired = []
        n = min(len(ch_entries), len(en_entries))
        for i in range(n):
            ch, en = ch_entries[i], en_entries[i]
            paired.append({
                "verse_range": ch["verse_range"],
                "level": ch["level"],
                "level_label_zh": ch["level_label"],
                "level_label_en": en["level_label"],
                "zh": ch["question"],
                "en": en["question"],
            })

        # Group consecutive entries sharing the same verse_range into one
        # unit — this is the "same-range depth / stacking" grouping.
        grouped: list[dict] = []
        for entry in paired:
            if grouped and grouped[-1]["verse_range"] == entry["verse_range"]:
                grouped[-1]["questions_by_level"][entry["level"]] = {
                    "zh": entry["zh"], "en": entry["en"],
                    "level_label_zh": entry["level_label_zh"],
                    "level_label_en": entry["level_label_en"],
                }
            else:
                grouped.append({
                    "verse_range": entry["verse_range"],
                    "questions_by_level": {
                        "observation": None,
                        "interpretation": None,
                        "application": None,
                        entry["level"]: {
                            "zh": entry["zh"], "en": entry["en"],
                            "level_label_zh": entry["level_label_zh"],
                            "level_label_en": entry["level_label_en"],
                        }
                    }
                })

        return {"questions": grouped}

    @classmethod
    def is_valid(cls, parsed: dict) -> bool:
        """Check that at least one question was successfully parsed."""
        return bool(parsed.get("questions"))

    @classmethod
    def flat_list(cls, parsed: dict) -> list[dict]:
        """
        Convenience accessor: flatten the grouped structure back into a
        single ordered list of individual questions, each tagged with its
        verse range and level. Useful for a simple UI that just wants to
        iterate questions in verse order without caring about grouping.
        """
        flat = []
        for group in parsed.get("questions", []):
            for level in ("observation", "interpretation", "application"):
                q = group["questions_by_level"].get(level)
                if q:
                    flat.append({
                        "verse_range": group["verse_range"],
                        "level": level,
                        "level_label_zh": q["level_label_zh"],
                        "level_label_en": q["level_label_en"],
                        "zh": q["zh"],
                        "en": q["en"],
                    })
        return flat
