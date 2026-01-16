# app/features/cafe_chatbot/retrieval/embedder.py

from sentence_transformers import SentenceTransformer
import numpy as np


class QueryEmbedder:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single user query.
        Returns a normalized vector suitable for cosine similarity.
        """
        vec = self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return vec
