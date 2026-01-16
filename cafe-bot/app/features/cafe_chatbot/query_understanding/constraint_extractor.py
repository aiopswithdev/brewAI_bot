# # app/features/cafe_chatbot/query_understanding/constraint_extractor.py
# import re
# import os
# import json
# import requests
# from typing import Optional, Dict
# from dotenv import load_dotenv

# load_dotenv()


# class LLMConstraintExtractor:
#     """
#     Uses an LLM to extract structured constraints from a user query.
#     This is a QUERY PLANNER, not a retriever or answer generator.
#     """

#     def __init__(
#         self,
#         api_key: Optional[str] = None,
#         # model_name: str = "gemini-2.5-flash",
#         model_name: str = "gemini-3-flash-preview",
#         timeout: int = 20
#     ):
#         self.api_key = api_key or os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise RuntimeError("GEMINI_API_KEY not set")

#         self.model_name = model_name
#         self.timeout = timeout
#         self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

#     # -----------------------------
#     # Public API
#     # -----------------------------
#     def _safe_json_parse(self, text: str) -> dict:
#         """
#         Extract JSON from LLM output that may include Markdown fences or text.
#         """

#         # 1. Remove Markdown ```json fences if present
#         text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

#         # 2. Try direct parse
#         try:
#             return json.loads(text)
#         except json.JSONDecodeError:
#             pass

#         # 3. Fallback: extract first JSON object
#         start = text.find("{")
#         end = text.rfind("}")

#         if start != -1 and end != -1 and end > start:
#             try:
#                 return json.loads(text[start:end + 1])
#             except json.JSONDecodeError:
#                 pass

#         raise ValueError("No valid JSON found in LLM output")
#     def extract(self, user_query: str, chat_history: Optional[list[dict]] = None) -> dict:
#         """
#         Returns a validated constraint dictionary.
#         Never raises on LLM failure — always returns a safe default.
#         """

#         prompt = self._build_prompt(user_query, chat_history)
#         payload = {
#             "contents": [
#                 {
#                     "parts": [{"text": prompt}]
#                 }
#             ],
#             "generationConfig": {
#                 "temperature": 0.0,
#                 "maxOutputTokens": 1000
#             }
#         }

#         endpoint = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"

#         try:
#             resp = requests.post(endpoint, json=payload, timeout=self.timeout)
#             resp.raise_for_status()
#             data = resp.json()

#             raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
#             print("=== RAW LLM OUTPUT ===")
#             print(raw_text)

#             parsed = self._safe_json_parse(raw_text)

#             return self._validate(parsed)

#         except Exception:
#             # FAIL SAFE: no constraints inferred
#             return self._empty_constraints()

#     # -----------------------------
#     # Prompting
#     # -----------------------------

#     def _build_prompt(self, user_query: str, chat_history: Optional[list[dict]] = None) -> str:
#         context_str=""
#         if chat_history:
#             # We only need the last 2 interactions for context to save tokens
#             recent_history = chat_history[-4:] 
#             context_str = "PREVIOUS CONVERSATION (Use this to inherit constraints like Price or Category):\n"
#             for msg in recent_history:
#                 role = "User" if msg["role"] == "user" else "Assistant"
#                 context_str += f"{role}: {msg['content']}\n"
#         return f"""
# You are a query understanding component for a cafe menu system.

# TASK:
# Extract structured constraints from the user query.
# Do NOT answer the question.
# Do NOT mention menu items.
# Do NOT guess.

# RULES:
# 1. INHERITANCE: If the user says "vegan ones" or "show me more", assume they keep the previous category (e.g., drinks) and price limits (e.g., <150) unless stated otherwise.
# 2. PRICE: "Budget is 150" means "max_price": 150.
# 3. CONTEXT: If previous turn was about "Drinks" and user says "vegan", imply "Vegan Drinks".

# {context_str}
# Return ONLY valid JSON in the following format:

# {{
#   "max_price": number | null,
#   "min_price": number | null,
#   "diet": [],
#   "temperature": [],
#   "milk": null,
#   "category_hint": string | null
# }}

# Rules:
# - If a constraint is not mentioned, return null or an empty list.
# - Never invent values.
# - Use numbers only for prices.

# User query:
# \"\"\"{user_query}\"\"\"
# """.strip()

#     # -----------------------------
#     # Validation & Safety
#     # -----------------------------

#     def _validate(self, data: Dict) -> Dict:
#         """
#         Strict validation to prevent LLM hallucinations.
#         """

#         safe = self._empty_constraints()

#         if isinstance(data.get("max_price"), (int, float)):
#             if 0 < data["max_price"] < 5000:
#                 safe["max_price"] = int(data["max_price"])

#         if isinstance(data.get("min_price"), (int, float)):
#             if 0 < data["min_price"] < 5000:
#                 safe["min_price"] = int(data["min_price"])

#         if isinstance(data.get("diet"), list):
#             safe["diet"] = [
#                 d for d in data["diet"]
#                 if d in {"vegan", "vegetarian"}
#             ]

#         if isinstance(data.get("temperature"), list):
#             safe["temperature"] = [
#                 t for t in data["temperature"]
#                 if t in {"hot", "cold"}
#             ]

#         if data.get("milk") in {"milk", "non-milk"}:
#             safe["milk"] = data["milk"]

#         if isinstance(data.get("category_hint"), str):
#             safe["category_hint"] = data["category_hint"].strip() or None

#         return safe

#     def _empty_constraints(self) -> Dict:
#         return {
#             "max_price": None,
#             "min_price": None,
#             "diet": [],
#             "temperature": [],
#             "milk": None,
#             "category_hint": None
#         }

"""Based on the logs and the file you uploaded, the issue is that your Constraint Extractor is "stateless". It looks at "show me vegan options" in isolation,
 sees no price mentioned in that specific sentence, and resets max_price to null.

To fix this, the Extractor must see the Chat History to inherit the budget from the previous turn."""

# app/features/cafe_chatbot/query_understanding/constraint_extractor.py
# import re
# import os
# import json
# import requests
# from typing import Optional, Dict, List
# from dotenv import load_dotenv

# load_dotenv()


# class LLMConstraintExtractor:
#     """
#     Uses an LLM to extract structured constraints from a user query.
#     This is a QUERY PLANNER, not a retriever or answer generator.
#     """

#     def __init__(
#         self,
#         api_key: Optional[str] = None,
#         model_name: str = "gemini-3-flash-preview",
#         timeout: int = 20
#     ):
#         self.api_key = api_key or os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise RuntimeError("GEMINI_API_KEY not set")

#         self.model_name = model_name
#         self.timeout = timeout
#         self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

#     # -----------------------------
#     # Public API
#     # -----------------------------
#     def _safe_json_parse(self, text: str) -> dict:
#         """
#         Extract JSON from LLM output that may include Markdown fences or text.
#         """
#         # 1. Remove Markdown ```json fences if present
#         text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()

#         # 2. Try direct parse
#         try:
#             return json.loads(text)
#         except json.JSONDecodeError:
#             pass

#         # 3. Fallback: extract first JSON object
#         start = text.find("{")
#         end = text.rfind("}")

#         if start != -1 and end != -1 and end > start:
#             try:
#                 return json.loads(text[start:end + 1])
#             except json.JSONDecodeError:
#                 pass

#         raise ValueError("No valid JSON found in LLM output")

#     def extract(self, user_query: str, chat_history: Optional[List[Dict]] = None) -> Dict:
#         """
#         Returns a validated constraint dictionary.
#         Never raises on LLM failure — always returns a safe default.
#         """

#         prompt = self._build_prompt(user_query, chat_history)

#         payload = {
#             "contents": [
#                 {
#                     "parts": [{"text": prompt}]
#                 }
#             ],
#             "generationConfig": {
#                 "temperature": 0.0,
#                 "maxOutputTokens": 1000
#             }
#         }

#         endpoint = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"

#         try:
#             resp = requests.post(endpoint, json=payload, timeout=self.timeout)
#             resp.raise_for_status()
#             data = resp.json()

#             raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
#             # Uncomment for debugging prompts
#             # print("=== RAW LLM OUTPUT ===")
#             # print(raw_text)

#             parsed = self._safe_json_parse(raw_text)

#             return self._validate(parsed)

#         except Exception as e:
#             print(f"[Extractor Error] {e}")
#             # FAIL SAFE: no constraints inferred
#             return self._empty_constraints()

#     # -----------------------------
#     # Prompting
#     # -----------------------------

#     def _build_prompt(self, user_query: str, chat_history: Optional[List[Dict]] = None) -> str:
        
#         context_str = ""
#         if chat_history:
#             # Only use the last 2 turns (User + Bot) to keep context tight
#             last_turns = chat_history[-4:]
#             context_str = "PREVIOUS CONVERSATION:\n"
#             for msg in last_turns:
#                 role = "User" if msg["role"] == "user" else "Assistant"
#                 context_str += f"{role}: {msg['content']}\n"

#         return f"""
# You are a query understanding component for a cafe menu system.

# TASK:
# Extract structured constraints from the LATEST user query.
# Do NOT answer the question. Do NOT mention menu items.

# RULES FOR CONTEXT:
# 1. **INHERITANCE**: If the user's query implies filtering the PREVIOUS results (e.g., "show me vegan ones", "what about cold ones"), you MUST inherit the constraints (like Price, Category) from the PREVIOUS CONVERSATION.
# 2. **OVERWRITE**: If the user explicitly sets a new value (e.g., "actually budget is 500"), overwrite the old one.
# 3. **RESET**: If the user changes the topic completely (e.g., "Where is the cafe located?"), reset constraints.

# {context_str}

# LATEST QUERY:
# \"\"\"{user_query}\"\"\"

# Return ONLY valid JSON in the following format:

# {{
#   "max_price": number | null,
#   "min_price": number | null,
#   "diet": [],
#   "temperature": [],
#   "milk": null,
#   "category_hint": string | null
# }}
# """.strip()

#     # -----------------------------
#     # Validation & Safety
#     # -----------------------------

#     def _validate(self, data: Dict) -> Dict:
#         """
#         Strict validation to prevent LLM hallucinations.
#         """

#         safe = self._empty_constraints()

#         if isinstance(data.get("max_price"), (int, float)):
#             if 0 < data["max_price"] < 5000:
#                 safe["max_price"] = int(data["max_price"])

#         if isinstance(data.get("min_price"), (int, float)):
#             if 0 < data["min_price"] < 5000:
#                 safe["min_price"] = int(data["min_price"])

#         if isinstance(data.get("diet"), list):
#             safe["diet"] = [
#                 d for d in data["diet"]
#                 if d in {"vegan", "vegetarian"}
#             ]

#         if isinstance(data.get("temperature"), list):
#             safe["temperature"] = [
#                 t for t in data["temperature"]
#                 if t in {"hot", "cold"}
#             ]

#         if data.get("milk") in {"milk", "non-milk"}:
#             safe["milk"] = data["milk"]

#         if isinstance(data.get("category_hint"), str):
#             safe["category_hint"] = data["category_hint"].strip() or None

#         return safe

#     def _empty_constraints(self) -> Dict:
#         return {
#             "max_price": None,
#             "min_price": None,
#             "diet": [],
#             "temperature": [],
#             "milk": None,
#             "category_hint": None
#         }


# ABOVE USED DEPRECATED GOOGLE MODULE
# BELOW IS USING THE LATEST ONE

import re
import os
import json
from typing import Optional, Dict, List
from dotenv import load_dotenv

# NEW SDK IMPORT
from google import genai
from google.genai import types

load_dotenv()

class LLMConstraintExtractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-flash-preview", # 2.0 is excellent for JSON extraction
        timeout: int = 20
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        # NEW: Initialize Client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def _safe_json_parse(self, text: str) -> dict:
        text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        # Fallback empty
        return {}

    def extract(self, user_query: str, chat_history: Optional[List[Dict]] = None) -> Dict:
        prompt = self._build_prompt(user_query, chat_history)

        try:
            # NEW SDK CALL
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=1000
                )
            )
            
            # The new SDK response object has a .text property
            return self._validate(self._safe_json_parse(response.text))

        except Exception as e:
            print(f"[Extractor Error] {e}")
            return self._empty_constraints()

    def _build_prompt(self, user_query: str, chat_history: Optional[List[Dict]] = None) -> str:
        context_str = "No previous conversation."
        if chat_history:
            last_turns = chat_history[-4:]
            context_str = ""
            for msg in last_turns:
                role = "User" if msg["role"] == "user" else "Assistant"
                context_str += f"{role}: {msg['content']}\n"

        return f"""
You are a query planner. Extract search constraints from the LATEST query.

### INSTRUCTIONS:
1. **INHERIT**: If the user's query is a follow-up (e.g., "show me vegan ones"), KEEP the constraints (Price, Category) from the conversation history.
2. **OVERWRITE**: If the user explicitly changes a value (e.g., "budget is 500"), use the new value.

### EXAMPLES:
History: "Suggest drinks under 200." -> Assistant: "Here are drinks..."
Current: "Show me the vegan ones"
Output: {{ "max_price": 200, "diet": ["vegan"], "category_hint": "drinks" }}

### REAL CONVERSATION:
{context_str}

**LATEST QUERY:** "{user_query}"

# Return ONLY valid JSON in the following format:

# {{
#   "max_price": number | null,
#   "min_price": number | null,
#   "diet": [],
#   "temperature": [],
#   "milk": null,
#   "category_hint": string | null
# }}
"""

    def _validate(self, data: Dict) -> Dict:
        safe = self._empty_constraints()
        if isinstance(data.get("max_price"), (int, float)) and 0 < data["max_price"] < 5000:
            safe["max_price"] = int(data["max_price"])
        if isinstance(data.get("min_price"), (int, float)) and 0 < data["min_price"] < 5000:
            safe["min_price"] = int(data["min_price"])
        if isinstance(data.get("diet"), list):
            safe["diet"] = [d for d in data["diet"] if d in {"vegan", "vegetarian"}]
        if isinstance(data.get("temperature"), list):
            safe["temperature"] = [t for t in data["temperature"] if t in {"hot", "cold"}]
        if data.get("milk") in {"milk", "non-milk"}:
            safe["milk"] = data["milk"]
        if isinstance(data.get("category_hint"), str):
            safe["category_hint"] = data["category_hint"].strip() or None
        return safe

    def _empty_constraints(self) -> Dict:
        return {
            "max_price": None, "min_price": None, "diet": [], 
            "temperature": [], "milk": None, "category_hint": None
        }