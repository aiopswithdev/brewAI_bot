# app/features/cafe_chatbot/retrieval/retriever.py

import json
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

from .embedder import QueryEmbedder


class CafeRAGRetriever:
    """
    Read-only RAG retriever.
    Loads FAISS index + metadata from disk and performs semantic retrieval.
    """

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)

        self.index = None
        self.metadata = []
        self.id_to_meta = {}
        self.embedder = None
        self.dimension = None

        self._load_storage()

    # -----------------------------
    # Storage loading
    # -----------------------------

    def _load_storage(self):
        index_path = self.storage_dir / "index.faiss"
        metadata_path = self.storage_dir / "metadata.jsonl"
        config_path = self.storage_dir / "config.json"

        if not index_path.exists():
            raise RuntimeError("FAISS index not found")

        if not metadata_path.exists():
            raise RuntimeError("metadata.jsonl not found")

        if not config_path.exists():
            raise RuntimeError("config.json not found")

        # Load config
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.dimension = config["dimension"]
        embedding_model = config["embedding_model"]

        # Load embedder
        self.embedder = QueryEmbedder(embedding_model)

        # Load FAISS index
        self.index = faiss.read_index(str(index_path))

        if self.index.d != self.dimension:
            raise RuntimeError("Embedding dimension mismatch")

        # Load metadata
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                self.metadata.append(record)
                self.id_to_meta[record["vector_id"]] = record

        if self.index.ntotal != len(self.metadata):
            raise RuntimeError("Index / metadata size mismatch")

    # -----------------------------
    # Public retrieval API
    # -----------------------------

    def search(
        self,
        query: str,
        top_k: int = 50,
        max_price: Optional[int] = None,
        require_in_stock: bool = True,
        diet: Optional[List[str]] = None, # <--- 1. Add this parameter  
        category_ids: Optional[List[str]] = None,
        subcategory_ids: Optional[List[str]] = None,
        group_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Perform hybrid semantic retrieval with optional filtering.
        """

        # Embed query
        query_vec = self.embedder.embed(query)

        # FAISS search
        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for vector_id, score in zip(indices[0], scores[0]):
            if vector_id == -1: continue

            item = self.id_to_meta.get(vector_id)
            if not item: continue

            # ---- EXISTING FILTERS ----
            if require_in_stock and not item.get("inStock", False): continue
            price = item.get("price")
            # Filter out if price is missing OR if it's too high
            if max_price is not None:
                if price is None or price > max_price:
                    continue

            # ---- NEW: DIET FILTER (The Logic Fix) ----
            if diet and "vegan" in diet:
                # We inspect the groupId string stored in metadata
                gid = item.get("groupId", "").lower()
                
                # Rule: Keep item ONLY if groupId suggests it is vegan
                # (looks for "nonmilk", "tea", "black", "manual", "brew")
                is_vegan_group = any(x in gid for x in ["nonmilk", "tea", "black", "manual"])
                
                if not is_vegan_group:
                    continue

            results.append({
                "item_id": item["item_id"],
                "name": item["name"],
                "price": item["price"],
                "categoryId": item["categoryId"],
                "subCategoryId": item["subCategoryId"],
                "groupId": item["groupId"],
                "score": float(score),
            })

        return results
