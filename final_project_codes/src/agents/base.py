import os
import time
import requests
import json
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

class BaseAgent(ABC):
    def __init__(self, model_name="llama3.1:8b", system_instruction=None):
        """
        Initialize the agent with Ollama backend.
        Default model is llama3.1:8b.
        """
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.history = []
        self.ollama_url = "http://localhost:11434/v1/chat/completions"

    @abstractmethod
    def run(self, user_input, case_id=None):
        """
        Execute the agent logic.
        """
        pass

    def _call_llm(self, prompt, retries=3):
        """
        Helper to call the local Ollama LLM with OpenAI-compatible API.
        Maps system_instruction and history to the messages array.
        """
        # 1. Build messages array
        messages = []
        
        # Add system instruction if present
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        
        # Add conversation history (windowed to last 8 entries to prevent context bloat)
        history_window = self.history[-8:] if len(self.history) > 8 else self.history
        for entry in history_window:
            role = "user" if entry["role"] == "user" else "assistant"
            messages.append({"role": role, "content": entry["content"]})
            
        # Add the current prompt as the final user instruction
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0,
            "top_p": 0.9,
            "max_tokens": 1000
        }

        for attempt in range(retries):
            try:
                response = requests.post(
                    self.ollama_url,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                
                result = response.json()
                text = result['choices'][0]['message']['content']
                
                # Usage metadata (Ollama might provide this in OpenAI format)
                usage_raw = result.get('usage', {})
                usage = {
                    "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                    "completion_tokens": usage_raw.get("completion_tokens", 0),
                    "total_tokens": usage_raw.get("total_tokens", 0)
                }
                
                return text, usage
                
            except requests.exceptions.RequestException as e:
                print(f"[LOCAL LLM ERROR] 連線失敗 (Attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return f"SYSTEM_ERROR: 連線至 Ollama 失敗。詳情: {str(e)}", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"[LOCAL LLM ERROR] 解析回應失敗: {e}")
                return "SYSTEM_ERROR: 解析 LLM 回應失敗", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return "SYSTEM_ERROR: API_UNAVAILABLE", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
