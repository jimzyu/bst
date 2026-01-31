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
