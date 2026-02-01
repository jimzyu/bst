"""
API client for Google Gemini with retry logic and parallel execution.
"""
import logging
import time
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass


class SheetsLogger:
    """Handles logging of drafts and final results to Google Sheets."""

    # Column layout (1-indexed, matching Google Sheets)
    COL_TIMESTAMP = 1
    COL_REFERENCE = 2
    COL_MODE = 3
    COL_DRAFT_1 = 4
    COL_DRAFT_2 = 5
    COL_DRAFT_3 = 6
    COL_FINAL_RESULT = 7

    HEADERS = [
        "Timestamp",
        "Reference",
        "Mode",
        "Draft 1 (Standard)",
        "Draft 2 (Historical)",
        "Draft 3 (Application)",
        "Final Result"
    ]

    def __init__(self, service_account_info: dict, spreadsheet_id: str):
        """
        Initialize Google Sheets logger.

        Args:
            service_account_info: Service account credentials dict from Streamlit secrets
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(creds)

        self.sheet = client.open_by_key(spreadsheet_id).sheet1
        self._ensure_headers()
        logger.info("SheetsLogger initialized successfully")

    def _ensure_headers(self):
        """Write header row if the sheet is empty."""
        if self.sheet.row_count == 0 or self.sheet.acell("A1").value is None:
            self.sheet.append_row(self.HEADERS)
            logger.info("Header row created in Google Sheet")

    def log_standard_study(self, reference: str, result: str):
        """
        Log a standard study session as a new row.

        Args:
            reference: Bible reference
            result: Generated study guide text
        """
        row = [
            datetime.now().isoformat(),   # Timestamp
            reference,                    # Reference
            "standard",                   # Mode
            "",                           # Draft 1 (not used in standard)
            "",                           # Draft 2 (not used in standard)
            "",                           # Draft 3 (not used in standard)
            result                        # Final Result
        ]
        self.sheet.append_row(row)
        logger.info(f"Standard study logged to Google Sheets for: {reference}")

    def log_deep_study(self, reference: str, drafts: List[str], final_result: str):
        """
        Log a deep study session with all drafts and final result as a new row.

        Args:
            reference: Bible reference
            drafts: List of 3 draft texts
            final_result: Merged final result text
        """
        row = [
            datetime.now().isoformat(),   # Timestamp
            reference,                    # Reference
            "deep",                       # Mode
            drafts[0],                    # Draft 1 (Standard)
            drafts[1],                    # Draft 2 (Historical)
            drafts[2],                    # Draft 3 (Application)
            final_result                  # Final Result
        ]
        self.sheet.append_row(row)
        logger.info(f"Deep study logged to Google Sheets for: {reference}")
        logger.info(f"  - Draft 1: {len(drafts[0])} chars")
        logger.info(f"  - Draft 2: {len(drafts[1])} chars")
        logger.info(f"  - Draft 3: {len(drafts[2])} chars")
        logger.info(f"  - Final:   {len(final_result)} chars")


class GeminiClient:
    """Client for interacting with Google Gemini API."""
    
    def __init__(self, api_key: str, system_instruction: str):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key
            system_instruction: System instruction for the model
        """
        genai.configure(api_key=api_key)
        
        generation_config = genai.types.GenerationConfig(
            temperature=Config.TEMPERATURE
        )
        
        self.model = genai.GenerativeModel(
            model_name=Config.MODEL_NAME,
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        
        # Initialize sheets logger if enabled
        self.draft_logger = None
        if Config.ENABLE_DRAFT_LOGGING:
            sheets_id = Config.get_google_sheets_id()
            service_account = Config.get_google_service_account()

            if sheets_id and service_account:
                self.draft_logger = SheetsLogger(service_account, sheets_id)
            else:
                logger.warning(
                    "Draft logging enabled but Google Sheets credentials are missing. "
                    "Check GOOGLE_SHEETS_ID and google_service_account in Streamlit secrets."
                )
        
        logger.info(f"Initialized Gemini client with model: {Config.MODEL_NAME}")
        logger.info(f"Draft logging: {'Enabled' if self.draft_logger else 'Disabled'}")
    
    @staticmethod
    def validate_response(response) -> str:
        """
        Validate Gemini API response.
        
        Args:
            response: Gemini API response object
            
        Returns:
            Response text if valid
            
        Raises:
            GeminiAPIError: If response is invalid or blocked
        """
        if not response:
            raise GeminiAPIError("Empty response from Gemini API")
        
        if not hasattr(response, 'text') or not response.text:
            raise GeminiAPIError("Response has no text content")
        
        # Check for content blocking
        if hasattr(response, 'prompt_feedback'):
            if hasattr(response.prompt_feedback, 'block_reason'):
                if response.prompt_feedback.block_reason:
                    raise GeminiAPIError(
                        f"Content blocked: {response.prompt_feedback.block_reason}"
                    )
        
        return response.text
    
    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GeminiAPIError, Exception)),
        reraise=True
    )
    def generate_content(self, prompt: str) -> str:
        """
        Generate content with retry logic.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text
            
        Raises:
            GeminiAPIError: If generation fails after retries
        """
        try:
            logger.info(f"Generating content (prompt length: {len(prompt)} chars)")
            response = self.model.generate_content(prompt)
            text = self.validate_response(response)
            logger.info(f"Successfully generated content (response length: {len(text)} chars)")
            return text
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise GeminiAPIError(f"Content generation failed: {str(e)}") from e
    
    def generate_drafts_parallel(self, prompts: List[str], 
                                 status_callback=None) -> List[str]:
        """
        Generate multiple drafts in parallel.
        
        Args:
            prompts: List of prompts to generate
            status_callback: Optional callback function to update UI status
            
        Returns:
            List of generated texts in same order as prompts
            
        Raises:
            GeminiAPIError: If any generation fails
        """
        logger.info(f"Generating {len(prompts)} drafts in parallel")
        start_time = time.time()
        
        drafts = [None] * len(prompts)
        
        with ThreadPoolExecutor(max_workers=min(len(prompts), 3)) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self.generate_content, prompt): i 
                for i, prompt in enumerate(prompts)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    drafts[index] = future.result()
                    if status_callback:
                        status_callback(f"Draft {index + 1} complete")
                    logger.info(f"Draft {index + 1} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Draft {index + 1} failed: {str(e)}")
                    raise GeminiAPIError(f"Draft {index + 1} generation failed: {str(e)}") from e
        
        elapsed = time.time() - start_time
        logger.info(f"All {len(prompts)} drafts completed in {elapsed:.2f} seconds")
        
        return drafts
    
    def generate_standard_study(self, reference: str, prompt: str) -> str:
        """
        Generate standard study guide (single request).
        
        Args:
            reference: Bible reference
            prompt: Study prompt
            
        Returns:
            Generated study guide text
        """
        logger.info(f"Generating standard study guide for: {reference}")
        result = self.generate_content(prompt)
        
        # Log to file if enabled
        if self.draft_logger:
            self.draft_logger.log_standard_study(reference, result)
        
        return result
    
    def generate_deep_study(self, reference: str, prompts: List[str], 
                           merge_prompt_template: str, status_callback=None) -> str:
        """
        Generate deep study guide (3 drafts + merge).
        
        Args:
            reference: Bible reference
            prompts: List of 3 prompts for drafts
            merge_prompt_template: Template string for merging (with {draft_1}, {draft_2}, {draft_3})
            status_callback: Optional callback for UI updates
            
        Returns:
            Final merged study guide text
            
        Raises:
            GeminiAPIError: If generation fails
        """
        logger.info(f"Starting deep study generation for: {reference}")
        
        # Generate 3 drafts in parallel
        drafts = self.generate_drafts_parallel(prompts, status_callback)
        
        # Check if any draft is invalid
        for i, draft in enumerate(drafts):
            if "[INVALID_REF]" in draft.upper():
                logger.warning(f"Invalid reference detected in draft {i + 1}")
                return "[INVALID_REF]"
        
        # Merge drafts
        if status_callback:
            status_callback("Merging drafts...")
        
        logger.info("Merging drafts into final study guide")
        
        # Build actual merge prompt with the drafts
        merge_prompt = merge_prompt_template.format(
            draft_1=drafts[0],
            draft_2=drafts[1],
            draft_3=drafts[2]
        )
        
        final_result = self.generate_content(merge_prompt)
        
        # Log to file if enabled
        if self.draft_logger:
            self.draft_logger.log_deep_study(reference, drafts, final_result)
        
        logger.info("Deep study generation complete")
        return final_result
