from typing import List, Dict, Generator
from .query_understanding.constraint_extractor import LLMConstraintExtractor
from .retrieval.retriever import CafeRAGRetriever
from .llm.generator import GeminiLLMResponseGenerator

class CafeChatbot:
    def __init__(self, storage_dir: str = "storage/cafe_faiss"):
        print("Initializing Cafe Chatbot...")
        self.extractor = LLMConstraintExtractor()
        self.retriever = CafeRAGRetriever(storage_dir)
        self.generator = GeminiLLMResponseGenerator(model_name="gemini-3-flash-preview")
        
        # Internal memory for local testing (so test_sota.py works)
        self.internal_memory: List[Dict[str, str]] = []

    def chat_stream(self, user_message: str, chat_history: List[Dict] = None) -> Generator[str, None, None]:
        """
        Orchestrates the pipeline and Yields response chunks.
        """
        active_history = chat_history if chat_history is not None else self.internal_memory
        # 🔥 Immediate flush token (perceived latency fix)
        yield "…\n"
        # 1. Extract Constraints (Context Aware)
        constraints = self.extractor.extract(user_message, chat_history=active_history)
        print(f"\n[DEBUG] Constraints: {constraints}")

        # 2. Retrieve Items
        # Use category_hint if available, otherwise fallback to raw user message
        search_query = constraints.get("category_hint") or user_message
        
        items = self.retriever.search(
            query=search_query,
            max_price=constraints.get("max_price"),
            diet=constraints.get("diet"),
            top_k=50 
        )
        print(f"[DEBUG] Retrieved {len(items)} items")
        print(items)
        # 3. Prepare history safely
        active_history.append({"role": "user", "content": user_message})
        assistant_msg = {"role": "assistant", "content": ""}
        active_history.append(assistant_msg)

        # 3. Generate & Stream Response
        # full_response = ""

        chunks: list[str] = []
        # Pass history to generator so LLM knows what we are talking about
        stream_gen = self.generator.generate_stream(
            user_query=user_message,
            items=items,
            chat_history=active_history
        )
        
        for chunk in stream_gen:
            # full_response += chunk
            # yield chunk
            chunks.append(chunk)
            yield chunk
        final_text = "".join(chunks)

        # Fix broken currency and word splits
        # Remove zero-width spaces
        assistant_msg["content"] = "".join(chunk)

        # 4. Update History (After full generation is complete)
        # active_history.append({"role": "user", "content": user_message})
        # active_history.append({"role": "assistant", "content": full_response})

    def clear_memory(self):
        self.history = []