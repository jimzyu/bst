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
    COL_USER_ANS_OBS = 8
    COL_FEEDBACK_OBS = 9
    COL_USER_ANS_INT = 10
    COL_FEEDBACK_INT = 11
    COL_USER_ANS_APP = 12
    COL_FEEDBACK_APP = 13
    COL_SCORE_OBS = 14
    COL_SCORE_INT = 15
    COL_SCORE_APP = 16
    COL_CONFIDENCE_OBS = 17
    COL_CONFIDENCE_INT = 18
    COL_CONFIDENCE_APP = 19
    COL_UNDERSTANDING_CONF = 20

    HEADERS = [
        "Timestamp",
        "Reference",
        "Mode",
        "Draft 1 (Standard)",
        "Draft 2 (Historical)",
        "Draft 3 (Application)",
        "Final Result / AI Answer Key",
        "User Answer - Observation",
        "Feedback - Observation",
        "User Answer - Interpretation",
        "Feedback - Interpretation",
        "User Answer - Application",
        "Feedback - Application",
        "Score - Observation",
        "Score - Interpretation",
        "Score - Application",
        "Confidence - Observation (%)",
        "Confidence - Interpretation (%)",
        "Confidence - Application (%)",
        "AI Understanding Confidence (%)"
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
        """Write or update header row to match current HEADERS definition."""
        try:
            # Get current first row
            current_headers = self.sheet.row_values(1) if self.sheet.row_count > 0 else []
            
            # Check if headers need updating
            headers_match = (current_headers == self.HEADERS)
            
            if not current_headers:
                # Sheet is empty, add headers
                self.sheet.append_row(self.HEADERS)
                logger.info("Header row created in Google Sheet")
            elif not headers_match:
                # Headers exist but don't match - update them
                logger.warning(f"Headers mismatch! Current: {len(current_headers)} cols, Expected: {len(self.HEADERS)} cols")
                logger.info("Updating header row to match current schema...")
                
                # Update the entire first row
                for i, header in enumerate(self.HEADERS, start=1):
                    self.sheet.update_cell(1, i, header)
                
                logger.info("Header row updated successfully")
            else:
                logger.info("Headers already match - no update needed")
                
        except Exception as e:
            logger.error(f"Error ensuring headers: {str(e)}")
            # If there's an error, try to append headers anyway
            if self.sheet.row_count == 0:
                self.sheet.append_row(self.HEADERS)

    def log_standard_study(self, reference: str, result: str):
        """
        Log a standard study session as a new row.

        Args:
            reference: Bible reference
            result: Generated study guide text
        """
        # Extract understanding confidence from result
        understanding_conf = self._extract_understanding_confidence(result)
        
        row = [
            datetime.now().isoformat(),   # Timestamp
            reference,                    # Reference
            "standard",                   # Mode
            "",                           # Draft 1 (not used in standard)
            "",                           # Draft 2 (not used in standard)
            "",                           # Draft 3 (not used in standard)
            result,                       # Final Result
            "", "", "", "", "", "",       # Empty quiz answer/feedback columns
            "", "", "",                   # Empty score columns
            "", "", "",                   # Empty confidence columns
            understanding_conf            # AI Understanding Confidence
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
        # Extract understanding confidence from final result
        understanding_conf = self._extract_understanding_confidence(final_result)
        
        row = [
            datetime.now().isoformat(),   # Timestamp
            reference,                    # Reference
            "deep",                       # Mode
            drafts[0],                    # Draft 1 (Standard)
            drafts[1],                    # Draft 2 (Historical)
            drafts[2],                    # Draft 3 (Application)
            final_result,                 # Final Result
            "", "", "", "", "", "",       # Empty quiz answer/feedback columns
            "", "", "",                   # Empty score columns
            "", "", "",                   # Empty confidence columns
            understanding_conf            # AI Understanding Confidence
        ]
        self.sheet.append_row(row)
        logger.info(f"Deep study logged to Google Sheets for: {reference}")
        logger.info(f"  - Draft 1: {len(drafts[0])} chars")
        logger.info(f"  - Draft 2: {len(drafts[1])} chars")
        logger.info(f"  - Draft 3: {len(drafts[2])} chars")
        logger.info(f"  - Final:   {len(final_result)} chars")

    def log_quiz_initial(self, reference: str, mode: str, answer_key: str, 
                        drafts: Optional[List[str]] = None) -> int:
        """
        Log initial quiz session and return the row number for later updates.

        Args:
            reference: Bible reference
            mode: "quiz_standard" or "quiz_deep"
            answer_key: AI-generated answer key (all 3 questions + answers)
            drafts: Optional list of 3 draft texts (for deep mode)

        Returns:
            Row number of the newly created entry
        """
        # Extract understanding confidence from answer key
        understanding_conf = self._extract_understanding_confidence(answer_key)
        
        row = [
            datetime.now().isoformat(),   # Timestamp
            reference,                    # Reference
            mode,                         # Mode
            drafts[0] if drafts else "",  # Draft 1
            drafts[1] if drafts else "",  # Draft 2
            drafts[2] if drafts else "",  # Draft 3
            answer_key,                   # AI Answer Key
            "", "", "", "", "", "",       # Empty quiz answer/feedback columns (will be filled later)
            "", "", "",                   # Empty score columns (will be filled later)
            "", "", "",                   # Empty confidence columns (will be filled later)
            understanding_conf            # AI Understanding Confidence
        ]
        self.sheet.append_row(row)
        row_number = self.sheet.row_count
        logger.info(f"Quiz session initialized in Google Sheets for: {reference} (row {row_number})")
        return row_number

    def log_quiz_answer(self, row_number: int, question_type: str, 
                       user_answer: str, feedback: str):
        """
        Update a specific quiz row with user answer, feedback, and score.

        Args:
            row_number: Row number in the sheet to update
            question_type: "observation", "interpretation", or "application"
            user_answer: User's submitted answer
            feedback: AI's qualitative feedback (includes score in parentheses)
        """
        # Map question type to column indices
        column_mapping = {
            "observation": (self.COL_USER_ANS_OBS, self.COL_FEEDBACK_OBS, self.COL_SCORE_OBS, self.COL_CONFIDENCE_OBS),
            "interpretation": (self.COL_USER_ANS_INT, self.COL_FEEDBACK_INT, self.COL_SCORE_INT, self.COL_CONFIDENCE_INT),
            "application": (self.COL_USER_ANS_APP, self.COL_FEEDBACK_APP, self.COL_SCORE_APP, self.COL_CONFIDENCE_APP)
        }

        if question_type not in column_mapping:
            logger.error(f"Invalid question type: {question_type}")
            return

        answer_col, feedback_col, score_col, confidence_col = column_mapping[question_type]
        
        # Extract score and confidence from feedback
        import re
        score_match = re.search(r'\((?:得分|Score):\s*(\d+)/10', feedback)
        score = score_match.group(1) if score_match else ""
        
        confidence_match = re.search(r'(?:信心度|Confidence):\s*(\d+)%', feedback)
        confidence = confidence_match.group(1) if confidence_match else ""

        # Use batch update to update all four cells at once (avoids rate limits)
        try:
            # Convert column numbers to A1 notation
            from gspread.utils import rowcol_to_a1
            
            answer_cell = rowcol_to_a1(row_number, answer_col)
            feedback_cell = rowcol_to_a1(row_number, feedback_col)
            score_cell = rowcol_to_a1(row_number, score_col)
            confidence_cell = rowcol_to_a1(row_number, confidence_col)
            
            # Small delay to avoid rate limits (especially for rapid submissions)
            import time
            time.sleep(0.5)
            
            # Batch update all four cells
            self.sheet.batch_update([
                {
                    'range': answer_cell,
                    'values': [[user_answer]]
                },
                {
                    'range': feedback_cell,
                    'values': [[feedback]]
                },
                {
                    'range': score_cell,
                    'values': [[score]]
                },
                {
                    'range': confidence_cell,
                    'values': [[confidence]]
                }
            ])
            
            logger.info(f"Quiz answer logged for {question_type} (row {row_number}, score: {score}/10, confidence: {confidence}%)")
            
        except Exception as e:
            logger.error(f"Failed to log quiz answer to Google Sheets: {str(e)}")
            logger.warning("Quiz will continue despite logging failure")
            # Don't raise - allow quiz to continue even if logging fails
    
    def _extract_understanding_confidence(self, text: str) -> str:
        """
        Extract understanding confidence percentage from text.
        
        Args:
            text: Text containing META_ASSESSMENT section
            
        Returns:
            Confidence percentage as string, or empty string if not found
        """
        import re
        pattern = r'Understanding Confidence:\s*(\d+)%'
        match = re.search(pattern, text)
        return match.group(1) if match else ""


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
                           build_merge_prompt, status_callback=None) -> str:
        """
        Generate deep study guide (3 drafts + merge).
        
        Args:
            reference: Bible reference
            prompts: List of 3 prompts for drafts
            build_merge_prompt: Callable that takes the list of drafts and returns the fully-formed merge prompt
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
        
        # Build the merge prompt now that drafts are available
        merge_prompt = build_merge_prompt(drafts)
        
        final_result = self.generate_content(merge_prompt)
        
        # Log to Google Sheets if enabled
        if self.draft_logger:
            self.draft_logger.log_deep_study(reference, drafts, final_result)
        
        logger.info("Deep study generation complete")
        return final_result

    def evaluate_answer(self, reference: str, question_type: str, question: str,
                       user_answer: str, ai_answer: str) -> str:
        """
        Evaluate user's answer against AI's answer with qualitative feedback.

        Args:
            reference: Bible reference
            question_type: "observation", "interpretation", or "application"
            question: The question that was asked
            user_answer: User's submitted answer
            ai_answer: AI's answer key for comparison

        Returns:
            Qualitative feedback text
        """
        from prompts import PromptTemplates
        
        logger.info(f"Evaluating {question_type} answer for: {reference}")
        
        evaluation_prompt = PromptTemplates.get_evaluation_prompt(
            reference=reference,
            question_type=question_type,
            question=question,
            user_answer=user_answer,
            ai_answer=ai_answer
        )
        
        feedback = self.generate_content(evaluation_prompt)
        logger.info(f"Evaluation complete ({len(feedback)} chars)")
        
        return feedback
