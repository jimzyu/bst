"""
Configuration settings for the Bible Study application.
"""
import streamlit as st
from typing import Optional


class Config:
    """Application configuration constants."""
    
    # Model settings
    MODEL_NAME = 'gemini-3-flash'
    TEMPERATURE = 0.3
    MAX_RETRIES = 3
    
    # Rate limiting
    REQUEST_COOLDOWN_SECONDS = 5
    
    # Logging settings
    ENABLE_DRAFT_LOGGING = True  # Set to False to disable Google Sheets logging
    
    # UI settings
    PAGE_TITLE = "聖經研讀工具 | Bible Study Tool"
    PAGE_ICON = "📖"
    
    # Text labels
    LABELS = {
        'main_title': '📖 聖經研讀工具',
        'subtitle': 'Bible Study Tool',
        'input_prompt': '輸入經文引用以獲取啟發提問與深度摘要。',
        'deep_mode': '🔍 啟用深度整合模式 (Deep Study Mode - Generates 3 drafts & merges them)',
        'input_placeholder': '例如: Matthew 14:1-36',
        'input_label': '經文引用 Scriptural Reference',
        'button_text': '開始研讀 Start Study',
        'error_invalid': '❌ 無法識別該經文引用。請輸入有效的聖經章節（例如：約翰福音 3:16）。',
        'error_invalid_en': 'Invalid scriptural reference. Please enter a valid Bible passage.',
        'error_empty': '請輸入有效的經文引用。',
        'status_deep': '正在進行深度研讀 (Conducting Deep Study)...',
        'status_standard': '正在查詢經文...',
        'status_complete': '完成！ (Complete!)',
        'reflections_title': '📝 提問+小結 (Reflections & Summary)',
        'summary_expander': '📖 查看主題摘要 (View Theme Summary)',
        'tab_traditional': '繁體中文',
        'tab_simplified': '简体中文',
        'tab_english': 'English',
    }
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Safely retrieve Gemini API key from Streamlit secrets."""
        try:
            return st.secrets["GEMINI_API_KEY"]
        except Exception:
            return None

    @staticmethod
    def get_google_sheets_id() -> Optional[str]:
        """Safely retrieve Google Sheets ID from Streamlit secrets."""
        try:
            return st.secrets["GOOGLE_SHEETS_ID"]
        except Exception:
            return None

    @staticmethod
    def get_google_service_account() -> Optional[dict]:
        """Safely retrieve Google service account credentials from Streamlit secrets."""
        try:
            return dict(st.secrets["google_service_account"])
        except Exception:
            return None

    @staticmethod
    def get_bible_api_key() -> Optional[str]:
        """Safely retrieve Bible API key from Streamlit secrets."""
        try:
            return st.secrets["BIBLE_API_KEY"]
        except Exception:
            return None
    
    @staticmethod
    def get_sandbox_mode() -> bool:
        """Check if sandbox mode is enabled."""
        try:
            return st.secrets.get("SANDBOX_MODE", False)
        except Exception:
            return False
    
    @staticmethod
    def get_sandbox_password() -> str:
        """Get sandbox password from secrets."""
        try:
            return st.secrets.get("SANDBOX_PASSWORD", "")
        except Exception:
            return ""

    @staticmethod
    def validate_api_key() -> bool:
        """Validate that API key exists and stop execution if not."""
        api_key = Config.get_api_key()
        if not api_key:
            st.error("⚠️ API Key not found. Please set 'GEMINI_API_KEY' in your Streamlit Secrets.")
            st.stop()
        return True
