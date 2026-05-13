import os
import time
import random
from abc import ABC, abstractmethod
from google import genai
from google.genai import errors
from dotenv import load_dotenv

load_dotenv()

class BaseAgent(ABC):
    def __init__(self, model_name="gemini-3.1-flash-lite", system_instruction=None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.history = []

    @abstractmethod
    def run(self, user_input, case_id=None):
        """
        Execute the agent logic.
        """
        pass

    def _call_llm(self, prompt, retries=8):
        """
        Helper to call the LLM with Enhanced Exponential Backoff and Jitter.
        Retries: 8 attempts with increasing backoff and snapshot cleaning.
        """
        full_prompt = f"{self.system_instruction}\n\n{prompt}" if self.system_instruction else prompt
        
        # Enhanced backoff strategy: longer waits for server errors
        backoff_times = [5, 10, 20, 40, 60, 90, 120, 150]
        
        for attempt in range(retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config={
                        "temperature": 0.0,
                        "top_p": 0.9,
                        "max_output_tokens": 1000,
                    }
                )
                
                text = response.text
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0
                }
                
                # Snapshot Integrity Check: If response is just a title or empty, treat as retryable failure
                incomplete_markers = ["--- Reflection Process ---", "Initial Draft:", "Reflection:", "Thought:"]
                is_empty_or_title_only = not text or any(text.strip() == m.strip() for m in incomplete_markers)
                
                if is_empty_or_title_only and attempt < retries - 1:
                    print(f"!!! Incomplete response detected (Attempt {attempt+1}). Retrying...")
                    time.sleep(2)
                    continue

                return text, usage
                
            except errors.ClientError as e:
                if "429" in str(e):
                    # Rate limit: wait longer with jitter
                    wait_time = 60 + (attempt * 30) + random.uniform(0, 10)
                    print(f"!!! 429 Rate Limit. Waiting {wait_time:.1f}s... (Attempt {attempt+1}/{retries})")
                    time.sleep(wait_time)
                else:
                    raise e
            except errors.ServerError as e:
                # Add jitter to backoff for server stability
                base_wait = backoff_times[attempt] if attempt < len(backoff_times) else 180
                jitter = random.uniform(0, base_wait * 0.2)
                wait_time = base_wait + jitter
                
                if "503" in str(e):
                    # Service unavailable: use even longer backoff for stability
                    wait_time = max(wait_time, 60 + jitter)
                    print(f"!!! 503 Service Unavailable. Waiting {wait_time:.1f}s... (Attempt {attempt+1}/{retries})")
                elif "500" in str(e):
                    print(f"!!! 500 Server Error. Waiting {wait_time:.1f}s... (Attempt {attempt+1}/{retries})")
                else:
                    print(f"!!! Server Error ({type(e).__name__}). Waiting {wait_time:.1f}s... (Attempt {attempt+1}/{retries})")
                
                time.sleep(wait_time)
            except Exception as e:
                print(f"!!! Fatal Error: {type(e).__name__} - {e}")
                raise e
        
        # Signal failure to the runner after all retries exhausted
        print(f"!!! All {retries} retry attempts exhausted. API remains unavailable.")
        return "SYSTEM_ERROR: API_UNAVAILABLE", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
