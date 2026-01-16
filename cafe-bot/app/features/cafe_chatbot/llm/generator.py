# import json
# import os
# import requests
# from typing import Optional
# from .prompt import SYSTEM_PROMPT, build_user_prompt
# from dotenv import load_dotenv

# load_dotenv()

# class GeminiLLMResponseGenerator:
#     def __init__(
#         self,
#         api_key: Optional[str] = None,
#         model_name: str = "gemini-1.5-flash-latestsss"
#     ):
#         # 1. Get the API Key from param or .env
#         self.api_key = api_key or os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise RuntimeError("GEMINI_API_KEY not set in .env")

#         self.model_name = model_name
#         # 2. Base URL should only go up to 'models'
#         self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

#     def generate_stream(
#         self,
#         user_query: str,
#         items: list[dict],
#         chat_history: list[dict] = None,
#         temperature: float = 0.2,
#         timeout: int = 60
#     ) -> str:
#         if not items:
#             return "Sorry, I couldn't find any matching items on the menu."

#         prompt_text = (
#             SYSTEM_PROMPT.strip()
#             + "\n\n"
#             # + build_user_prompt(user_query, items)
#         )
#         if chat_history:
#             prompt_text += "--- CONVERSATION HISTORY ---\n"
#             for msg in chat_history[-6:]: # Keep last 3 turns context
#                 role = "User" if msg["role"] == "user" else "Assistant"
#                 prompt_text += f"{role}: {msg['content']}\n"
#             prompt_text += "---------------------------\n\n"

#         prompt_text += build_user_prompt(user_query, items)

#         payload = {
#             "contents": [
#                 {
#                     "parts": [{"text": prompt_text}],
#                 }
#             ],
#             "generationConfig": {
#                 "temperature": temperature,
#                 "maxOutputTokens": 2000,
#             },
#         }

#         # 3. Correct URL Construction
#         endpoint = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"

#         try:
#             with requests.post(endpoint, json=payload, stream=True, timeout=timeout) as resp:
#                 resp.raise_for_status()
#                 # 3. Parse the stream
#                 # Gemini REST stream returns a JSON list: [ {part}, {part} ]
#                 # We iterate lines to parse valid JSON chunks.
#                 for line in resp.iter_lines():
#                     if not line:
#                         continue
                    
#                     decoded_line = line.decode('utf-8').strip()
                    
#                     # Clean up the JSON array formatting (remove [ , ])
#                     if decoded_line.startswith('['): decoded_line = decoded_line[1:]
#                     if decoded_line.endswith(']'): decoded_line = decoded_line[:-1]
#                     if decoded_line.startswith(','): decoded_line = decoded_line[1:]
                    
#                     if not decoded_line:
#                         continue

#                     try:
#                         chunk_data = json.loads(decoded_line)
#                         # Extract text from the deep JSON structure
#                         if "candidates" in chunk_data:
#                             text_chunk = chunk_data["candidates"][0]["content"]["parts"][0]["text"].strip()
#                             yield text_chunk
#                     except json.JSONDecodeError:
#                         continue # Skip incomplete chunks
#             # data = resp.json()

#             # return (
#             #     data["candidates"][0]
#             #     ["content"]["parts"][0]
#             #     ["text"]
#             #     .strip()
#             # )

#         except Exception as e:
#             # Check if it's a 401/403 (Key issue) or 404 (URL issue)
#             if hasattr(e, 'response') and e.response is not None:
#                 print(f"Status Code: {e.response.status_code}")
#                 print(f"Response: {e.response.text}")
#             else:
#                 print(f"Error: {e}")

#             return "I'm having trouble connecting to my brain. Here's what I found: " + \
#                    ", ".join(f"{i['name']} (₹{i['price']})" for i in items)
#         # except Exception as e:
#         #     print(e)

#             # HARD FAIL-SAFE (do not remove)
#             # return (
#             #     "Here are some options you can choose from: "
#             #     + ", ".join(f"{i['name']} (₹{i['price']})" for i in items)
#             # )

"""
This happens because the requests library struggles to parse the raw streaming JSON from Gemini (which often comes "pretty-printed" or split across lines), causing the code to skip chunks silently.

To make this Production-Ready and fix the silence, we should use the official Google SDK. It handles streaming connections and parsing natively, making it faster and bulletproof.
"""
# import os
# import google.generativeai as genai
# from typing import List, Dict, Generator, Optional
# from .prompt import SYSTEM_PROMPT, build_user_prompt
# from dotenv import load_dotenv

# load_dotenv()

# class GeminiLLMResponseGenerator:
#     def __init__(
#         self,
#         api_key: Optional[str] = None,
#         model_name: str = "gemini-2.5-flash" # Or "gemini-1.5-flash" if 2.5 isn't available
#     ):
#         self.api_key = api_key or os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise RuntimeError("GEMINI_API_KEY not set")
        
#         # Configure the official SDK
#         genai.configure(api_key=self.api_key)
#         self.model = genai.GenerativeModel(model_name)

#     def generate_stream(
#         self,
#         user_query: str,
#         items: list[dict],
#         chat_history: Optional[List[Dict]] = None,
#         temperature: float = 0.2,
#         timeout: int = 10 # SDK handles timeouts differently, but keeping arg for compatibility
#     ) -> Generator[str, None, None]:
#         """
#         Yields chunks of text using the official SDK's native streaming.
#         """
#         if not items:
#             yield "Sorry, I couldn't find any matching items on the menu."
#             return

#         # 1. Build Prompt
#         full_prompt = SYSTEM_PROMPT.strip() + "\n\n"
        
#         if chat_history:
#             full_prompt += "--- CONVERSATION HISTORY ---\n"
#             for msg in chat_history[-6:]: 
#                 role = "User" if msg["role"] == "user" else "Assistant"
#                 full_prompt += f"{role}: {msg['content']}\n"
#             full_prompt += "---------------------------\n\n"

#         full_prompt += build_user_prompt(user_query, items)

#         # 2. Generate Stream (Robust & Fast)
#         try:
#             response_stream = self.model.generate_content(
#                 full_prompt,
#                 stream=True,
#                 generation_config=genai.types.GenerationConfig(
#                     temperature=temperature,
#                     max_output_tokens=1000
#                 )
#             )

#             # 3. Yield Text Chunks
#             for chunk in response_stream:
#                 if chunk.text:
#                     yield chunk.text

#         except Exception as e:
#             print(f"Streaming Error: {e}")
#             yield "I'm having trouble connecting to my brain right now."

#     def generate(self, user_query: str, items: list[dict], chat_history: Optional[List[Dict]] = None) -> str:
#         """
#         Non-streaming fallback.
#         """
#         full_response = ""
#         for chunk in self.generate_stream(user_query, items, chat_history):
#             full_response += chunk
#         return full_response


# FOR GEMINI-3-FLASH=PREVIEW

# import os
# import google.generativeai as genai
# from typing import List, Dict, Generator, Optional
# from .prompt import SYSTEM_PROMPT, build_user_prompt
# from dotenv import load_dotenv

# load_dotenv()

# class GeminiLLMResponseGenerator:
#     def __init__(
#         self,
#         api_key: Optional[str] = None,
#         # Using the model you specified (ensure this string is exactly right for your access)
#         model_name: str = "gemini-1.5-flash" # fallback default
#     ):
#         self.api_key = api_key or os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise RuntimeError("GEMINI_API_KEY not set")
        
#         genai.configure(api_key=self.api_key)
#         self.model = genai.GenerativeModel(model_name)

#     def generate_stream(
#         self,
#         user_query: str,
#         items: list[dict],
#         chat_history: Optional[List[Dict]] = None,
#         temperature: float = 0.2,
#         timeout: int = 10 
#     ) -> Generator[str, None, None]:
        
#         if not items:
#             yield "Sorry, I couldn't find any matching items on the menu."
#             return

#         # 1. Build Prompt
#         full_prompt = SYSTEM_PROMPT.strip() + "\n\n"
        
#         if chat_history:
#             full_prompt += "--- CONVERSATION HISTORY ---\n"
#             for msg in chat_history[-6:]: 
#                 role = "User" if msg["role"] == "user" else "Assistant"
#                 full_prompt += f"{role}: {msg['content']}\n"
#             full_prompt += "---------------------------\n\n"

#         full_prompt += build_user_prompt(user_query, items)

#         # 2. Safety Settings (CRITICAL FIX)
#         # Block nothing. Menus are safe, but AI often flags "Cocktail" or "Killer" as unsafe.
#         safety_settings = [
#             {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
#             {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
#             {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
#             {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
#         ]

#         # 3. Generate Stream
#         try:
#             response_stream = self.model.generate_content(
#                 full_prompt,
#                 stream=True,
#                 generation_config=genai.types.GenerationConfig(
#                     temperature=temperature,
#                     max_output_tokens=2048  # Increased limit
#                 ),
#                 safety_settings=safety_settings
#             )

#             # 4. Robust Chunk Iteration
#             for chunk in response_stream:
#                 try:
#                     # Accessing .text on a 'finish_reason' chunk can raise ValueError
#                     # We simply ignore chunks that have no text
#                     if chunk.text:
#                         yield chunk.text
#                 except ValueError:
#                     pass  # Skip metadata-only chunks safely

#         except Exception as e:
#             print(f"Streaming Error: {e}")
#             yield f"[Connection Error: {str(e)}]"

#     def generate(self, user_query: str, items: list[dict], chat_history: Optional[List[Dict]] = None) -> str:
#         """
#         Non-streaming fallback.
#         """
#         full_response = ""
#         for chunk in self.generate_stream(user_query, items, chat_history):
#             full_response += chunk
#         return full_response

# ABOVE USED DEPRECATED GOOGLE MODULE
# BELOW IS USING THE LATEST ONE
import os
from typing import List, Dict, Generator, Optional
from dotenv import load_dotenv

# NEW SDK IMPORT
from google import genai
from google.genai import types

from .prompt import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

class GeminiLLMResponseGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        # You can use "gemini-1.5-flash" or "gemini-2.0-flash"
        model_name: str = "gemini-3-flash-preview" 
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        
        # NEW: Initialize the Client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate_stream(
        self,
        user_query: str,
        items: list[dict],
        chat_history: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        timeout: int = 20
    ) -> Generator[str, None, None]:
        
        if not items:
            yield "Sorry, I couldn't find any matching items on the menu."
            return

        # 1. Build Prompt
        full_prompt = SYSTEM_PROMPT.strip() + "\n\n"
        
        if chat_history:
            full_prompt += "--- CONVERSATION HISTORY ---\n"
            for msg in chat_history[-6:]: 
                role = "User" if msg["role"] == "user" else "Assistant"
                full_prompt += f"{role}: {msg['content']}\n"
            full_prompt += "---------------------------\n\n"

        full_prompt += build_user_prompt(user_query, items)

        # 2. Safety Settings (NEW SYNTAX)
        # We explicitly disable blocks to prevent menu items like "Killer Brownie" triggering filters
        safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE"
            ),
        ]

        # 3. Generate Stream (NEW SYNTAX)
        try:
            # The method is now on the 'client.models' accessor
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                    safety_settings=safety_settings
                )
            )

            # 4. Iteration
            for chunk in response_stream:
                # The new SDK chunk object has a .text property that is robust
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            print(f"Streaming Error: {e}")
            yield f"[Connection Error: {str(e)}]"

    def generate(self, user_query: str, items: list[dict], chat_history: Optional[List[Dict]] = None) -> str:
        """
        Non-streaming fallback.
        """
        full_response = ""
        for chunk in self.generate_stream(user_query, items, chat_history):
            full_response += chunk
        return full_response