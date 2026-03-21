"""
Session state management for the Bible Study application.
"""
import time
import streamlit as st
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StudyRecord:
    """Record of a single study session."""
    reference: str
    timestamp: float
    deep_mode: bool
    final_result: str
    drafts: Optional[list] = None
    error: Optional[str] = None
    
    def get_datetime(self) -> str:
        """Get formatted datetime string."""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")


class SessionManager:
    """Manage Streamlit session state for the application."""
    
    @staticmethod
    def initialize():
        """Initialize all session state variables."""
        if 'ai_result' not in st.session_state:
            st.session_state.ai_result = None
        
        if 'study_history' not in st.session_state:
            st.session_state.study_history = []
        
        if 'current_drafts' not in st.session_state:
            st.session_state.current_drafts = None
        
        if 'last_request_time' not in st.session_state:
            st.session_state.last_request_time = 0.0
        
        if 'request_count' not in st.session_state:
            st.session_state.request_count = 0
        
        if 'total_errors' not in st.session_state:
            st.session_state.total_errors = 0
        
        # Quiz mode state
        if 'quiz_active' not in st.session_state:
            st.session_state.quiz_active = False
        
        if 'quiz_current_question' not in st.session_state:
            st.session_state.quiz_current_question = 0  # 0=observation, 1=interpretation, 2=application
        
        if 'quiz_answer_key' not in st.session_state:
            st.session_state.quiz_answer_key = None
        
        if 'quiz_questions' not in st.session_state:
            st.session_state.quiz_questions = {}  # {type: question_text}
        
        if 'quiz_user_answers' not in st.session_state:
            st.session_state.quiz_user_answers = {}  # {type: user_answer}
        
        if 'quiz_feedbacks' not in st.session_state:
            st.session_state.quiz_feedbacks = {}  # {type: ai_feedback}
        
        if 'quiz_reference' not in st.session_state:
            st.session_state.quiz_reference = None
        
        if 'quiz_sheets_row' not in st.session_state:
            st.session_state.quiz_sheets_row = None
        
        if 'quiz_case_study' not in st.session_state:
            st.session_state.quiz_case_study = None  # Stores (chinese, english) tuple

        # Sub-question tracking
        if 'quiz_current_subquestion' not in st.session_state:
            st.session_state.quiz_current_subquestion = 0  # Index within current question's sub-questions

        if 'quiz_subquestion_answers' not in st.session_state:
            st.session_state.quiz_subquestion_answers = {}  # {question_type: [answer1, answer2, ...]}

        # Emphasis study mode state
        if 'emphasis_active' not in st.session_state:
            st.session_state.emphasis_active = False

        if 'emphasis_selected' not in st.session_state:
            st.session_state.emphasis_selected = None  # 'explore', 'understand', or 'apply'

        if 'emphasis_reference' not in st.session_state:
            st.session_state.emphasis_reference = None

        if 'emphasis_result' not in st.session_state:
            st.session_state.emphasis_result = None
    
    @staticmethod
    def can_make_request(cooldown_seconds: int) -> tuple[bool, float]:
        """
        Check if enough time has passed since last request.
        
        Args:
            cooldown_seconds: Minimum seconds between requests
            
        Returns:
            Tuple of (can_proceed, seconds_remaining)
        """
        time_since_last = time.time() - st.session_state.last_request_time
        
        if time_since_last < cooldown_seconds:
            return False, cooldown_seconds - time_since_last
        
        return True, 0.0
    
    @staticmethod
    def record_request():
        """Record that a request was made."""
        st.session_state.last_request_time = time.time()
        st.session_state.request_count += 1
    
    @staticmethod
    def record_error():
        """Record that an error occurred."""
        st.session_state.total_errors += 1
    
    @staticmethod
    def save_study_result(reference: str, deep_mode: bool, result: str,
                         drafts: Optional[list] = None, error: Optional[str] = None):
        """
        Save study result to history.
        
        Args:
            reference: Bible reference
            deep_mode: Whether deep mode was used
            result: Final result text
            drafts: Optional list of draft texts (for deep mode)
            error: Optional error message
        """
        record = StudyRecord(
            reference=reference,
            timestamp=time.time(),
            deep_mode=deep_mode,
            final_result=result,
            drafts=drafts,
            error=error
        )
        
        st.session_state.study_history.append(record)
        st.session_state.ai_result = result
        st.session_state.current_drafts = drafts
    
    @staticmethod
    def get_current_result() -> Optional[str]:
        """Get the current AI result."""
        return st.session_state.ai_result
    
    @staticmethod
    def get_study_history() -> list:
        """Get all study history."""
        return st.session_state.study_history
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get session statistics."""
        return {
            'total_requests': st.session_state.request_count,
            'total_errors': st.session_state.total_errors,
            'total_studies': len(st.session_state.study_history),
            'last_request_time': st.session_state.last_request_time
        }
    
    @staticmethod
    def clear_current_result():
        """Clear the current result."""
        st.session_state.ai_result = None
        st.session_state.current_drafts = None
    
    @staticmethod
    def show_debug_info():
        """Display debug information (for development)."""
        with st.expander("🔧 Debug Info"):
            stats = SessionManager.get_stats()
            st.write("**Session Statistics:**")
            st.json(stats)
            
            if st.session_state.study_history:
                st.write("**Recent Studies:**")
                for i, record in enumerate(reversed(st.session_state.study_history[-5:])):
                    st.write(f"{i+1}. {record.reference} - {record.get_datetime()} - Deep: {record.deep_mode}")
    

    # Emphasis Study Mode Methods

    @staticmethod
    def start_emphasis(reference: str, emphasis: str, result: str):
        st.session_state.emphasis_active = True
        st.session_state.emphasis_selected = emphasis
        st.session_state.emphasis_reference = reference
        st.session_state.emphasis_result = result

    @staticmethod
    def end_emphasis():
        st.session_state.emphasis_active = False
        st.session_state.emphasis_selected = None
        st.session_state.emphasis_reference = None
        st.session_state.emphasis_result = None

    # Quiz Mode Methods
    
    @staticmethod
    def start_quiz(reference: str, answer_key: str, questions: dict, 
                  case_study: tuple = None, sheets_row: int = None):
        """
        Initialize a new quiz session.
        
        Args:
            reference: Bible reference
            answer_key: Full AI-generated answer key
            questions: Dict of {question_type: question_text}
            case_study: Tuple of (chinese_case_study, english_case_study)
            sheets_row: Google Sheets row number for logging
        """
        st.session_state.quiz_active = True
        st.session_state.quiz_current_question = 0
        st.session_state.quiz_reference = reference
        st.session_state.quiz_answer_key = answer_key
        st.session_state.quiz_questions = questions
        st.session_state.quiz_user_answers = {}
        st.session_state.quiz_feedbacks = {}
        st.session_state.quiz_sheets_row = sheets_row
        st.session_state.quiz_case_study = case_study
        st.session_state.quiz_current_subquestion = 0
        st.session_state.quiz_subquestion_answers = {}
    
    @staticmethod
    def get_current_question_type() -> str:
        """Get the current question type."""
        question_types = ["observation", "interpretation", "application"]
        index = st.session_state.quiz_current_question
        if index < len(question_types):
            return question_types[index]
        return None
    
    @staticmethod
    def save_quiz_answer(question_type: str, user_answer: str, feedback: str):
        """Save user's answer and feedback for a question."""
        st.session_state.quiz_user_answers[question_type] = user_answer
        st.session_state.quiz_feedbacks[question_type] = feedback
    
    @staticmethod
    def advance_to_next_question():
        """Move to the next question in the quiz."""
        st.session_state.quiz_current_question += 1
        st.session_state.quiz_current_subquestion = 0  # Reset sub-question index

    @staticmethod
    def advance_to_next_subquestion():
        """Move to the next sub-question within the current question."""
        st.session_state.quiz_current_subquestion += 1

    @staticmethod
    def save_subquestion_answer(question_type: str, answer: str):
        """Append a sub-question answer for the given question type."""
        if question_type not in st.session_state.quiz_subquestion_answers:
            st.session_state.quiz_subquestion_answers[question_type] = []
        st.session_state.quiz_subquestion_answers[question_type].append(answer)

    @staticmethod
    def get_subquestion_answers(question_type: str) -> list:
        """Get all collected sub-question answers for a question type."""
        return st.session_state.quiz_subquestion_answers.get(question_type, [])
    
    @staticmethod
    def is_quiz_complete() -> bool:
        """Check if all quiz questions have been answered."""
        return st.session_state.quiz_current_question >= 3
    
    @staticmethod
    def end_quiz():
        """End the current quiz session."""
        st.session_state.quiz_active = False
        st.session_state.quiz_current_question = 0
        st.session_state.quiz_answer_key = None
        st.session_state.quiz_questions = {}
        st.session_state.quiz_user_answers = {}
        st.session_state.quiz_feedbacks = {}
        st.session_state.quiz_reference = None
        st.session_state.quiz_sheets_row = None
        st.session_state.quiz_case_study = None
        st.session_state.quiz_current_subquestion = 0
        st.session_state.quiz_subquestion_answers = {}
