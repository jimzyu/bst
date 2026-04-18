"""
API client for Google Gemini with retry logic and parallel execution.
"""
import base64
import logging
import time
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import requests
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

    def log_emphasis_study(self, reference: str, emphasis: str, question_set: str):
        """
        Log an emphasis study session when user selects an emphasis.
        Mode stored as 'emphasis_explore', 'emphasis_understand', or 'emphasis_apply'.
        """
        understanding_conf = self._extract_understanding_confidence(question_set)
        row = [
            datetime.now().isoformat(),
            reference,
            f"emphasis_{emphasis}",
            "", "", "",           # drafts not used
            question_set,         # question set as final result
            "", "", "", "", "", "",  # quiz answers/feedback empty
            "", "", "",           # scores empty
            "", "", "",           # evaluation confidence empty
            understanding_conf
        ]
        self.sheet.insert_row(row, index=2)
        logger.info(f"Emphasis study logged for: {reference} (emphasis: {emphasis}, inserted at row 2)")
        return 2

    def log_emphasis_quiz_answer(self, row_number: int, question_type: str,
                                  user_answer: str, feedback: str):
        """
        Update an emphasis quiz row with answer, feedback, and score.
        Reuses the same column mapping as log_quiz_answer.
        """
        self.log_quiz_answer(row_number, question_type, user_answer, feedback)


class GlooTokenManager:
    """
    Manages OAuth2 client credentials token exchange for Gloo AI Studio.
    Caches the access token and refreshes it when expired.
    Token endpoint: https://platform.ai.gloo.com/oauth2/token
    Tokens expire after 3600 seconds (1 hour).
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    def get_token(self) -> str:
        """Return a valid access token, refreshing if expired."""
        import time
        # Refresh 60 seconds before expiry to avoid race conditions
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        self._refresh_token()
        return self._token

    def _refresh_token(self):
        """Exchange client credentials for a new access token."""
        import base64
        import time
        import requests as req

        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        response = req.post(
            Config.GLOO_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth}"
            },
            data={
                "grant_type": "client_credentials",
                "scope": "api/access"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        self._token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expiry = time.time() + expires_in
        logger.info("Gloo access token refreshed successfully")



class GeminiClient:
    """Client for interacting with Google Gemini API."""
    
    def __init__(self, api_key: str, system_instruction: str):
        """
        Initialize the AI client. Uses Gloo AI Studio if Config.USE_GLOO is True,
        otherwise uses Google Gemini directly.

        Args:
            api_key: Gemini API key (ignored when USE_GLOO is True)
            system_instruction: System instruction for the model
        """
        self.system_instruction = system_instruction
        self._use_gloo = Config.USE_GLOO
        self.model = None          # Gemini GenerativeModel (non-Gloo only)
        self._gloo_token_mgr = None  # GlooTokenManager (Gloo only)

        if self._use_gloo:
            client_id, client_secret = Config.get_gloo_credentials()
            self._gloo_token_mgr = GlooTokenManager(client_id, client_secret)
            logger.info(f"Initialized Gloo client with model: {Config.MODEL_NAME}")
        else:
            genai.configure(api_key=api_key)
            generation_config = genai.types.GenerationConfig(
                temperature=Config.TEMPERATURE
            )
            self.model = genai.GenerativeModel(
                model_name=Config.MODEL_NAME,
                generation_config=generation_config,
                system_instruction=system_instruction
            )
            logger.info(f"Initialized Gemini client with model: {Config.MODEL_NAME}")

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
        logger.info(f"Draft logging: {'Enabled' if self.draft_logger else 'Disabled'}")
    
    # ── Gloo token management ──────────────────────────────────────────────────

    def _refresh_gloo_token(self):
        """Fetch a new Gloo access token using client credentials OAuth2 flow."""
        auth = base64.b64encode(
            f"{self._gloo_client_id}:{self._gloo_client_secret}".encode()
        ).decode()
        response = requests.post(
            Config.GLOO_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth}"
            },
            data={"grant_type": "client_credentials", "scope": "api/access"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        self._gloo_token = data["access_token"]
        # expires_in is in seconds; subtract 60s buffer
        self._gloo_token_expiry = time.time() + data.get("expires_in", 3600) - 60
        logger.info("Gloo access token refreshed")

    def _get_gloo_token(self) -> str:
        """Return a valid Gloo access token, refreshing if expired."""
        if time.time() >= self._gloo_token_expiry:
            self._refresh_gloo_token()
        return self._gloo_token

    def _call_gloo(self, prompt: str) -> str:
        """Make a single chat completion call via Gloo REST API."""
        token = self._get_gloo_token()
        response = requests.post(
            f"{Config.GLOO_API_BASE}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            json={
                "model": Config.MODEL_NAME,
                "temperature": Config.TEMPERATURE,
                "messages": [
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user",   "content": prompt}
                ]
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    # ── Response validation (Gemini path only) ──────────────────────────────

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

    def generate_content_quality(self, prompt: str) -> str:
        """
        Generate content using the quality model for the active provider.
        Use for: scenario generation, evaluation, follow-up/redirect questions.
        Falls back to standard generate_content for Option 1 (Gemini direct).
        """
        try:
            logger.info(f"Generating quality content (prompt length: {len(prompt)} chars)")
            if self._use_anthropic:
                text = self._generate_via_anthropic(prompt,
                                                     model=Config.ANTHROPIC_MODEL_QUALITY)
            elif self._use_gloo:
                text = self._generate_via_gloo(prompt,
                                               model=Config.GLOO_MODEL_QUALITY)
            else:
                response = self.model.generate_content(prompt)
                text = self.validate_response(response)
            logger.info(f"Quality content generated ({len(text)} chars)")
            return text
        except Exception as e:
            logger.error(f"Error generating quality content: {str(e)}")
            raise GeminiAPIError(f"Quality content generation failed: {str(e)}") from e

    def generate_content(self, prompt: str) -> str:
        """
        Generate content with retry logic.
        Routes to Gloo AI Studio or Gemini depending on Config.USE_GLOO.

        Args:
            prompt: Input prompt

        Returns:
            Generated text

        Raises:
            GeminiAPIError: If generation fails after retries
        """
        try:
            logger.info(f"Generating content (prompt length: {len(prompt)} chars)")

            if self._use_gloo:
                text = self._generate_via_gloo(prompt)
            else:
                response = self.model.generate_content(prompt)
                text = self.validate_response(response)

            logger.info(f"Successfully generated content (response length: {len(text)} chars)")
            return text

        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise GeminiAPIError(f"Content generation failed: {str(e)}") from e

    def _generate_via_gloo(self, prompt: str, model: str = None) -> str:
        """Call Gloo's OpenAI-compatible completions endpoint.
        Args:
            prompt: Input prompt
            model: Model override; defaults to GLOO_MODEL_FAST
        """
        import requests as req
        model = model or Config.GLOO_MODEL_FAST
        token = self._gloo_token_mgr.get_token()
        response = req.post(
            f"{Config.GLOO_API_BASE}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user",   "content": prompt}
                ],
                "temperature": Config.TEMPERATURE
            },
            timeout=180
        )
        if not response.ok:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            logger.error(f"Gloo API error {response.status_code}: {error_body}")
            raise GeminiAPIError(f"Gloo {response.status_code}: {error_body}")
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        if not text:
            raise GeminiAPIError("Gloo returned empty response")
        return text
    
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
    
    def map_passage_teaching_points(self, reference: str) -> list:
        """
        Map a passage's distinct teaching points using the passage mapping prompt.

        Args:
            reference: Bible reference

        Returns:
            List of dicts with keys: verses, teaching, diagnosis
        """
        import re
        from prompts import PromptTemplates

        logger.info(f"Mapping teaching points for: {reference}")
        prompt = PromptTemplates.get_passage_mapping_prompt(reference)
        raw = self.generate_content(prompt)

        # Parse structured TEACHING_POINT_N blocks
        points = []
        blocks = re.split(r'TEACHING_POINT_\d+', raw)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            verses_m = re.search(r'Verses:\s*(.+)', block)
            teaching_m = re.search(r'Teaching:\s*(.+)', block)
            teaching_zh_m = re.search(r'Teaching_ZH:\s*(.+)', block)
            diagnosis_m = re.search(r'Diagnosis:\s*(.+?)(?=\n[A-Z]|$)', block, re.DOTALL)
            if teaching_m:
                points.append({
                    'verses': verses_m.group(1).strip() if verses_m else '',
                    'teaching': teaching_m.group(1).strip(),
                    'teaching_zh': teaching_zh_m.group(1).strip() if teaching_zh_m else '',
                    'diagnosis': diagnosis_m.group(1).strip() if diagnosis_m else '',
                })

        logger.info(f"Found {len(points)} teaching point(s)")
        return points

    def generate_case_study(self, reference: str) -> str:
        """
        Generate a threshold scenario (case study) for the given passage.

        Args:
            reference: Bible reference

        Returns:
            Generated text containing [THRESHOLD_SCENARIO_CHINESE] and
            [THRESHOLD_SCENARIO_ENGLISH] sections
        """
        from prompts import PromptTemplates
        logger.info(f"Generating case study for: {reference}")
        prompt = PromptTemplates.get_threshold_prompt(reference)
        result = self.generate_content_quality(prompt)
        logger.info(f"Case study generated ({len(result)} chars)")
        return result

    def generate_all_emphasis_parallel(
            self,
            reference: str,
            status_callback=None
        ) -> tuple[dict[str, str], str]:
        """
        Generate all three emphasis question sets and a passage summary in parallel.
        Runs four API calls concurrently: Explore, Understand, Apply, and Summary.

        Args:
            reference: Bible reference (e.g. '雅各書1:19-27')
            status_callback: Optional callable for UI status updates during generation

        Returns:
            Tuple of (emphasis_dict, summary_text):
              - emphasis_dict: {'explore': text, 'understand': text, 'apply': text}
              - summary_text: Raw summary text containing [CHINESE] and [ENGLISH] sections
        """
        from prompts import PromptTemplates

        prompts_dict = PromptTemplates.get_all_emphasis_prompts(reference)
        emphasis_keys = list(prompts_dict.keys())  # ['explore', 'understand', 'apply']
        summary_prompt = PromptTemplates.get_summary_prompt(reference)

        # Run all four in parallel: 3 emphasis + 1 summary
        all_prompts = [prompts_dict[k] for k in emphasis_keys] + [summary_prompt]

        logger.info(f"Generating 3 emphasis sets + summary in parallel for: {reference}")
        results_list = self.generate_drafts_parallel(all_prompts, status_callback)

        emphasis_results = {emphasis_keys[i]: results_list[i] for i in range(len(emphasis_keys))}
        summary_text = results_list[-1]

        return emphasis_results, summary_text

    def generate_followup_question(self, reference: str, question_type: str,
                                    emphasis: str, original_question: str,
                                    user_answer: str, missing_note: str) -> tuple:
        """
        Generate a targeted follow-up question when the student's answer was incomplete.

        Args:
            reference: Bible reference
            question_type: 'observation', 'interpretation', or 'application'
            emphasis: 'explore', 'understand', or 'apply'
            original_question: The question the student answered
            user_answer: The student's original answer
            missing_note: The [MISSING] note from the evaluation — what was not covered

        Returns:
            Tuple of (chinese_question, english_question)
        """
        from prompts import PromptTemplates
        prompt = PromptTemplates.FOLLOWUP_QUESTION_TEMPLATE.format(
            reference=reference,
            question_type=question_type,
            emphasis=emphasis,
            original_question=original_question,
            user_answer=user_answer,
            missing_note=missing_note
        )
        raw = self.generate_content_quality(prompt)
        # Parse [CHINESE]: ... and [ENGLISH]: ... lines
        import re
        ch_match = re.search(r'\[CHINESE\]:\s*(.+?)(?=\[ENGLISH\]|$)', raw, re.DOTALL)
        en_match = re.search(r'\[ENGLISH\]:\s*(.+?)$', raw, re.DOTALL)
        ch_q = ch_match.group(1).strip() if ch_match else raw.strip()
        en_q = en_match.group(1).strip() if en_match else ''
        return ch_q, en_q

    def generate_redirect_question(self, reference: str, question_type: str,
                                    emphasis: str, original_question: str,
                                    user_answer: str, correction_note: str) -> tuple:
        """
        Generate a gentle redirect question when the student's answer was inaccurate.
        Guides them back to re-read a specific part of the text without signalling error.

        Returns:
            Tuple of (chinese_question, english_question)
        """
        from prompts import PromptTemplates
        prompt = PromptTemplates.REDIRECT_QUESTION_TEMPLATE.format(
            reference=reference,
            question_type=question_type,
            emphasis=emphasis,
            original_question=original_question,
            user_answer=user_answer,
            correction_note=correction_note
        )
        raw = self.generate_content(prompt)
        import re
        ch_match = re.search(r'\[CHINESE\]:\s*(.+?)(?=\[ENGLISH\]|$)', raw, re.DOTALL)
        en_match = re.search(r'\[ENGLISH\]:\s*(.+?)$', raw, re.DOTALL)
        ch_q = ch_match.group(1).strip() if ch_match else raw.strip()
        en_q = en_match.group(1).strip() if en_match else ''
        return ch_q, en_q

    def evaluate_answer(self, reference: str, question_type: str, question: str,
                       user_answer: str, ai_answer: str, emphasis: str = "standard") -> str:
        """
        Evaluate user's answer against AI's answer with qualitative feedback.

        Args:
            reference: Bible reference
            question_type: "observation", "interpretation", or "application"
            question: The question that was asked
            user_answer: User's submitted answer
            ai_answer: AI's answer key for comparison
            emphasis: One of 'explore', 'understand', 'apply', or 'standard'

        Returns:
            Qualitative feedback text
        """
        from prompts import PromptTemplates
        
        logger.info(f"Evaluating {question_type} answer for: {reference} (emphasis: {emphasis})")
        
        evaluation_prompt = PromptTemplates.get_evaluation_prompt(
            reference=reference,
            question_type=question_type,
            question=question,
            user_answer=user_answer,
            ai_answer=ai_answer,
            emphasis=emphasis
        )
        
        feedback = self.generate_content_quality(evaluation_prompt)
        logger.info(f"Evaluation complete ({len(feedback)} chars)")
        
        return feedback
