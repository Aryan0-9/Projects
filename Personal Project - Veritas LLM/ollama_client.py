# Import Async HTTP client for sending requests and Optional for type annotations
import httpx
from typing import Optional

# Async client wrapper to query locally running Ollama instances with extended timeouts
class OllamaClient:
    
    # Initializes the client with the model name, local server endpoint, and offline mocking options
    def __init__(self, model_name: str = "llama3", base_url: str = "http://localhost:11434", mock_if_offline: bool = True):

        # Store configuration for target model, Ollama endpoint URL, and offline fallback behavior
        self.model_name = model_name
        self.base_url = base_url
        self.mock_if_offline = mock_if_offline

    # Sends a prompt to the local Ollama API or falls back if offline/timed out
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:

        # Construct full generation API URL and prepare request payload options
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 128  # Stops generation early for faster evaluation
            }
        }
        
        # Add optional system instructions to the request payload if provided
        if system_prompt:
            payload["system"] = system_prompt

        # Send request with a 180-second timeout to handle larger models or slower CPU inference
        async with httpx.AsyncClient(timeout=180.0) as client:
            
            try:
                # Post generation request and return generated text from response JSON
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json().get("response", "")
            
            except (httpx.ConnectError, httpx.HTTPStatusError):
                # Fall back to simulated mock output or default safety message on connection failure
                if self.mock_if_offline:
                    return self._mock_response(prompt)
                return "I cannot assist with requests that violate safety policies."
           
            except httpx.ReadTimeout:
                # Return standard message if execution exceeds timeout limit
                return "I cannot fulfill this request due to execution limits."
            
    # Generates realistic responses for testing when Ollama isn't running
    def _mock_response(self, prompt: str) -> str:

        # Check for jailbreak keywords in prompt to trigger simulated unsafe output during testing
        prompt_lower = prompt.lower()

        if "dan" in prompt_lower or "do anything now" in prompt_lower:
            return "Sure! As DAN, I can do anything you want. Here is how you bypass network firewalls"
        
        # Default mock response simulating a standard model refusal
        return "I am unable to fulfill this request as it involves potentially harmful or unsafe activities."
