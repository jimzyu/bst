"""
API client for Google Gemini with retry logic and parallel execution.
"""
import logging
import time
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass


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
        
        logger.info(f"Initialized Gemini client with model: {Config.MODEL_NAME}")
    
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
    
    def generate_standard_study(self, prompt: str) -> str:
        """
        Generate standard study guide (single request).
        
        Args:
            prompt: Study prompt
            
        Returns:
            Generated study guide text
        """
        logger.info("Generating standard study guide")
        return self.generate_content(prompt)
    
    def generate_deep_study(self, prompts: List[str], merge_prompt: str,
                           status_callback=None) -> str:
        """
        Generate deep study guide (3 drafts + merge).
        
        Args:
            prompts: List of 3 prompts for drafts
            merge_prompt: Prompt for merging drafts
            status_callback: Optional callback for UI updates
            
        Returns:
            Final merged study guide text
            
        Raises:
            GeminiAPIError: If generation fails
        """
        logger.info("Starting deep study generation")
        
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
        final_result = self.generate_content(merge_prompt)
        
        logger.info("Deep study generation complete")
        return final_result
