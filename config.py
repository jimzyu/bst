"""
Configuration settings for the Bible Study application.
"""
import streamlit as st
from typing import Optional


class Config:
    """Application configuration constants."""

    # ── API mode — choose ONE ────────────────────────────────────────────────
    #
    # OPTION 1: Gemini direct (development/testing — fast and cheap)
    #   USE_GLOO = False, USE_ANTHROPIC = False
    #
    # OPTION 2: Anthropic direct mixed (quality output, no proxy overhead)
    #   USE_GLOO = False, USE_ANTHROPIC = True
    #   Fast tasks → Haiku 4.5 | Quality tasks → Sonnet 4.6
    #
    # OPTION 3: Gloo mixed (cross-provider, one credential, proxy overhead)
    #   USE_GLOO = True, USE_ANTHROPIC = False
    #   Fast tasks → gloo-google-gemini-2.5-flash | Quality → gloo-anthropic-claude-sonnet-4.6
    #
    USE_GLOO = True
    USE_ANTHROPIC = False

    # ── Model names ───────────────────────────────────────────────────────────

    # Option 1 — Gemini direct (testing — both tasks use Flash)
    GEMINI_MODEL_FAST    = 'gemini-2.5-flash'   # summary, mapping, questions
    GEMINI_MODEL_QUALITY = 'gemini-2.5-pro'   # scenario, eval, follow-up
    # GEMINI_MODEL_QUALITY = 'gemini-2.5-pro'   # uncomment for quality runs

    # Option 2 — Anthropic direct (mixed)
    ANTHROPIC_MODEL_QUALITY = 'claude-sonnet-4-6'   # scenario, eval, follow-up
    ANTHROPIC_MODEL_FAST    = 'claude-haiku-4-5'    # summary, mapping, questions

    # Option 3 — Gloo mixed (cross-provider)
    GLOO_MODEL_QUALITY = 'gloo-anthropic-claude-sonnet-4.6'        # quality tasks
    # GLOO_MODEL_QUALITY = 'gloo-anthropic-claude-sonnet-4.6' # alternative quality model
    GLOO_MODEL_FAST    = 'gloo-google-gemini-2.5-flash'      # fast tasks

    # Legacy single-model Gloo name (kept for reference)
    GLOO_MODEL_NAME = GLOO_MODEL_FAST
    TEMPERATURE = 0.3
    MAX_RETRIES = 3

    # Gloo endpoints
    GLOO_TOKEN_URL = 'https://platform.ai.gloo.com/oauth2/token'
    GLOO_API_BASE  = 'https://platform.ai.gloo.com/ai/v2'
    
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
        """Retrieve active API key — Gemini key or Gloo credentials depending on USE_GLOO."""
        try:
            if Config.USE_GLOO:
                return st.secrets.get("GLOO_CLIENT_ID")
            return st.secrets["GEMINI_API_KEY"]
        except Exception:
            return None

    @staticmethod
    def get_anthropic_api_key() -> Optional[str]:
        """Retrieve Anthropic API key from Streamlit secrets."""
        try:
            return st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            return None

    @staticmethod
    def get_gloo_credentials() -> tuple:
        """Retrieve Gloo Client ID and Client Secret from Streamlit secrets."""
        try:
            client_id = st.secrets["GLOO_CLIENT_ID"]
            client_secret = st.secrets["GLOO_CLIENT_SECRET"]
            return client_id, client_secret
        except Exception:
            return None, None

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
        """Validate that API credentials exist and stop execution if not."""
        if Config.USE_ANTHROPIC:
            key = Config.get_anthropic_api_key()
            if not key:
                st.error("⚠️ Anthropic API key not found. Please set 'ANTHROPIC_API_KEY' in your Streamlit Secrets.")
                st.stop()
        elif Config.USE_GLOO:
            client_id, client_secret = Config.get_gloo_credentials()
            if not client_id or not client_secret:
                st.error("⚠️ Gloo credentials not found. Please set 'GLOO_CLIENT_ID' and 'GLOO_CLIENT_SECRET' in your Streamlit Secrets.")
                st.stop()
        else:
            api_key = Config.get_api_key()
            if not api_key:
                st.error("⚠️ API Key not found. Please set 'GEMINI_API_KEY' in your Streamlit Secrets.")
                st.stop()
        return True
